import os
import time
import threading
import ctypes
from ctypes import windll, wintypes, byref, Structure, c_ulong, POINTER, sizeof
import psutil
from loguru import logger
import win32security
import win32api
import win32con
import sys

from ctypes import c_long

# 导入ConfigManager
from config.config_manager import ConfigManager

# 定义NTSTATUS类型
NTSTATUS = c_long
wintypes.NTSTATUS = NTSTATUS

# Windows API 常量
PROCESS_ALL_ACCESS = 0x1F0FFF
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
MEM_RELEASE = 0x8000
PAGE_READWRITE = 0x04
IDLE_PRIORITY_CLASS = 0x40

# 系统信息类别
SystemFileCacheInformation = 0x15
SystemMemoryListInformation = 0x50
SystemCombinePhysicalMemoryInformation = 0x82

# 内存列表命令
MemoryEmptyWorkingSets = 0x2
MemoryFlushModifiedList = 0x3
MemoryPurgeStandbyList = 0x4
MemoryPurgeLowPriorityStandbyList = 0x5

# 系统文件缓存信息结构
class SYSTEM_FILECACHE_INFORMATION(Structure):
    _fields_ = [
        ("CurrentSize", ctypes.c_size_t),
        ("PeakSize", ctypes.c_size_t),
        ("PageFaultCount", wintypes.ULONG),
        ("MinimumWorkingSet", ctypes.c_size_t),
        ("MaximumWorkingSet", ctypes.c_size_t),
        ("CurrentSizeIncludingTransitionInPages", ctypes.c_size_t),
        ("PeakSizeIncludingTransitionInPages", ctypes.c_size_t),
        ("TransitionRePurposeCount", wintypes.ULONG),
        ("Flags", wintypes.ULONG),
    ]

# 内存合并信息结构
class MEMORY_COMBINE_INFORMATION_EX(Structure):
    _fields_ = [
        ("Handle", wintypes.HANDLE),
        ("PagesCombined", ctypes.c_ulonglong),
        ("Flags", wintypes.ULONG),
    ]

class MemoryCleanerManager:
    """内存清理管理器类"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MemoryCleanerManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # 配置
        self.clean_switches = [False] * 6
        self.brute_mode = True
        self.enabled = False  # 添加内存清理开关状态
        
        # 自定义配置项
        self.clean_interval = 300  # 清理间隔，默认300秒
        self.threshold = 80.0  # 内存占用触发阈值，默认80%
        self.cooldown_time = 60  # 清理冷却时间，默认60秒
        
        # 状态
        self.running = False
        self._clean_thread = None
        self._last_threshold_clean = 0  # 最后一次基于阈值的清理时间
        
        # 清理统计
        self.total_cleaned_mb = 0
        self.last_cleaned_mb = 0
        self.clean_count = 0
        self.last_clean_time = None
        
        # 获取配置管理器
        self.config_manager = ConfigManager()
        
        # Windows API
        self.ntdll = ctypes.WinDLL('ntdll.dll')
        
        # 获取NtSetSystemInformation函数
        self.NtSetSystemInformation = self.ntdll.NtSetSystemInformation
        self.NtSetSystemInformation.restype = wintypes.NTSTATUS
        self.NtSetSystemInformation.argtypes = [
            wintypes.ULONG, 
            wintypes.LPVOID, 
            wintypes.ULONG
        ]
        
        # 获取NtQuerySystemInformation函数
        self.NtQuerySystemInformation = self.ntdll.NtQuerySystemInformation
        self.NtQuerySystemInformation.restype = wintypes.NTSTATUS
        self.NtQuerySystemInformation.argtypes = [
            wintypes.ULONG, 
            wintypes.LPVOID, 
            wintypes.ULONG, 
            POINTER(wintypes.ULONG)
        ]
        
        # 初始化提权
        self._init_privileges()
        
        # 从配置管理器加载配置
        self.update_from_config_manager()
        
        self._initialized = True
    
    def _init_privileges(self):
        """初始化并提升程序权限"""
        try:
            # 获取当前进程句柄
            hProcess = win32api.GetCurrentProcess()
            
            # 打开进程令牌
            hToken = win32security.OpenProcessToken(
                hProcess,
                win32security.TOKEN_ADJUST_PRIVILEGES | win32security.TOKEN_QUERY
            )
            
            # 智能权限分组
            # 1. 核心权限 - 内存清理必需，失败则功能受限
            core_privileges = [
                win32security.SE_INCREASE_QUOTA_NAME,     # 提高内存配额权限，系统缓存清理必需
                "SeProfileSingleProcessPrivilege",        # 单进程分析权限，清理工作集必需
            ]
            
            # 2. 增强权限 - 提升性能和功能，但不是必需
            enhanced_privileges = [
                win32security.SE_DEBUG_NAME,              # 最关键的调试权限，用于访问其他进程
                win32security.SE_INC_WORKING_SET_NAME,    # 增加工作集权限
                win32security.SE_MANAGE_VOLUME_NAME,      # 管理卷权限，文件系统缓存操作
            ]
            
            # 记录权限状态
            privilege_status = {
                "core": {"total": len(core_privileges), "acquired": 0},
                "enhanced": {"total": len(enhanced_privileges), "acquired": 0},
            }
            privilege_details = {}
            
            # 先请求核心权限 - 单独处理每一个，确保最大成功率
            for privilege_name in core_privileges:
                result = self._request_single_privilege(hToken, privilege_name)
                privilege_details[privilege_name] = result
                if result["success"]:
                    privilege_status["core"]["acquired"] += 1
            
            # 请求增强权限
            for privilege_name in enhanced_privileges:
                result = self._request_single_privilege(hToken, privilege_name)
                privilege_details[privilege_name] = result
                if result["success"]:
                    privilege_status["enhanced"]["acquired"] += 1
            
            # 关闭句柄
            win32api.CloseHandle(hToken)
            
            # 根据权限获取情况确定运行模式
            self.available_functions = {
                "trim_all_processes": privilege_status["core"]["acquired"] > 0,
                "flush_system_cache": privilege_status["core"]["acquired"] > 0,
                "memory_combine": privilege_status["enhanced"]["acquired"] > 0,
                "purge_standby_list": privilege_status["core"]["acquired"] > 0,
                "debug_other_processes": "SE_DEBUG_NAME" in privilege_details and 
                                        privilege_details["SE_DEBUG_NAME"]["success"]
            }
            
            # 记录权限获取结果
            logger.debug(f"权限获取状态: 核心权限 {privilege_status['core']['acquired']}/{privilege_status['core']['total']}," 
                        f" 增强权限 {privilege_status['enhanced']['acquired']}/{privilege_status['enhanced']['total']}")
            
            # 获取管理员状态
            is_admin = self._check_admin_rights()
            
            # 评估运行能力
            if privilege_status["core"]["acquired"] == 0:
                logger.warning("未能获取任何核心权限，内存清理功能将严重受限")
                if not is_admin:
                    logger.warning("建议以管理员身份运行程序以获得更好的内存清理效果")
            elif privilege_status["core"]["acquired"] < privilege_status["core"]["total"]:
                logger.warning("部分核心权限获取失败，某些内存清理功能可能受限")
            
            # 返回是否获取了足够权限
            return privilege_status["core"]["acquired"] > 0
                
        except Exception as e:
            logger.error(f"权限提升过程出现严重错误: {str(e)}")
            self.available_functions = {
                "trim_all_processes": False,
                "flush_system_cache": False,
                "memory_combine": False,
                "purge_standby_list": False,
                "debug_other_processes": False
            }
            return False
    
    def _request_single_privilege(self, hToken, privilege_name):
        """请求单个权限并返回详细结果"""
        result = {
            "name": privilege_name,
            "success": False,
            "error_code": None,
            "error_message": None
        }
        
        try:
            # 查找权限ID
            privilege_id = win32security.LookupPrivilegeValue(None, privilege_name)
            
            # 创建权限结构
            new_privilege = [(privilege_id, win32security.SE_PRIVILEGE_ENABLED)]
            
            # 应用权限
            win32security.AdjustTokenPrivileges(hToken, False, new_privilege)
            
            # 检查是否真正成功
            error_code = win32api.GetLastError()
            result["error_code"] = error_code
            
            if error_code == 0:
                result["success"] = True
                logger.debug(f"成功获取权限: {privilege_name}")
            else:
                if error_code == 1300:  # ERROR_NOT_ALL_ASSIGNED
                    result["error_message"] = "权限不足，通常只有系统进程才能获取此权限"
                    logger.debug(f"无法获取权限 {privilege_name}: 权限不足 (ERROR_NOT_ALL_ASSIGNED)")
                else:
                    result["error_message"] = f"错误码: {error_code}"
                    logger.warning(f"无法获取权限 {privilege_name}: 错误码 {error_code}")
        
        except Exception as e:
            result["error_message"] = str(e)
            logger.debug(f"请求权限 {privilege_name} 出现异常: {str(e)}")
        
        return result
    
    def _check_admin_rights(self):
        """检查当前进程是否拥有管理员权限"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    
    def _request_admin_rights(self):
        """请求提升为管理员权限（此函数需谨慎使用，可能导致程序重启）"""
        try:
            if not self._check_admin_rights():
                # 获取当前可执行文件路径
                executable = sys.executable
                # 重新以管理员身份启动
                ctypes.windll.shell32.ShellExecuteW(
                    None, 
                    "runas", 
                    executable,
                    " ".join(sys.argv),
                    None, 
                    1  # SW_SHOWNORMAL
                )
                # 退出当前进程
                sys.exit(0)
            return True
        except Exception as e:
            logger.error(f"请求管理员权限失败: {str(e)}")
            return False
    
    def update_from_config_manager(self):
        """从配置管理器更新设置"""
        if not hasattr(self, 'config_manager'):
            self.config_manager = ConfigManager()
        
        self.enabled = self.config_manager.memory_cleaner_enabled
        self.brute_mode = self.config_manager.memory_cleaner_brute_mode
        self.clean_switches = self.config_manager.memory_cleaner_switches.copy()
        
        # 加载自定义配置
        self.clean_interval = self.config_manager.memory_cleaner_interval
        self.threshold = self.config_manager.memory_cleaner_threshold
        self.cooldown_time = self.config_manager.memory_cleaner_cooldown
        
        # 确保清理间隔不低于60秒
        if self.clean_interval < 60:
            logger.warning(f"配置的清理间隔({self.clean_interval}秒)小于最小值60秒，将重置为60秒")
            self.clean_interval = 60
            self.config_manager.memory_cleaner_interval = 60
            self.config_manager.save_config()
        
        # 检查是否应该启动或停止清理线程
        self._check_should_run_thread()
        
        logger.debug("已从配置管理器更新内存清理设置")
    
    def _check_should_run_thread(self):
        """检查是否应该运行清理线程"""
        should_run = self.enabled and any(self.clean_switches)
        
        if should_run and not self.running:
            # 如果应该运行但未运行，则启动线程
            self.start_cleaner_thread()
            logger.debug("已启动内存清理线程")
        elif not should_run and self.running:
            # 如果不应该运行但正在运行，则停止线程
            self.stop_cleaner_thread()
            logger.debug("已停止内存清理线程，因为未启用任何清理选项")
    
    def sync_to_config_manager(self):
        """将当前设置同步到配置管理器"""
        if not hasattr(self, 'config_manager'):
            self.config_manager = ConfigManager()
        
        self.config_manager.memory_cleaner_enabled = self.enabled
        self.config_manager.memory_cleaner_brute_mode = self.brute_mode
        self.config_manager.memory_cleaner_switches = self.clean_switches.copy()
        
        # 同步自定义配置
        self.config_manager.memory_cleaner_interval = self.clean_interval
        self.config_manager.memory_cleaner_threshold = self.threshold
        self.config_manager.memory_cleaner_cooldown = self.cooldown_time
        
        # 保存配置
        self.config_manager.save_config()
        logger.debug("已将内存清理设置同步到配置管理器")
    
    def _record_cleaned_memory(self, mb_cleaned):
        """记录清理的内存量"""
        self.last_cleaned_mb = mb_cleaned
        self.total_cleaned_mb += mb_cleaned
        self.clean_count += 1
        self.last_clean_time = time.time()
    
    def _get_memory_before_clean(self):
        """获取清理前的内存信息，用于计算清理量"""
        try:
            mem = psutil.virtual_memory()
            return mem.available
        except Exception:
            return 0
            
    def trim_process_working_set(self):
        """清理所有进程的工作集"""
        try:
            # 获取清理前的可用内存
            before_available = self._get_memory_before_clean()
            
            # 根据可用权限选择最佳方法
            if not self.available_functions.get("trim_all_processes", False):
                logger.warning("缺少清理工作集所需权限，操作可能受限")
            
            # 如果使用暴力模式，直接使用Windows API清理所有进程工作集
            if self.brute_mode and self.available_functions.get("trim_all_processes", False):
                logger.debug("使用暴力模式清理所有进程工作集")
                command = MemoryEmptyWorkingSets
                status = self.NtSetSystemInformation(
                    SystemMemoryListInformation,
                    byref(wintypes.ULONG(command)),
                    sizeof(wintypes.ULONG)
                )
                
                # 记录状态码并判断是否成功
                if status == 0:  # STATUS_SUCCESS
                    logger.debug("暴力模式工作集清理成功，状态码: 0 (STATUS_SUCCESS)")
                else:
                    logger.error(f"暴力模式工作集清理失败，错误码: {status}")
                    # 失败时回退到逐个进程模式
                    self._trim_processes_individually()
            else:
                # 常规模式：逐个进程清理
                self._trim_processes_individually()
            
            # 计算清理的内存量
            after_available = self._get_memory_before_clean()
            cleaned_mb = max(0, (after_available - before_available) / (1024 * 1024))
            self._record_cleaned_memory(cleaned_mb)
            logger.debug(f"清理进程工作集完成，释放了 {cleaned_mb:.2f}MB 内存")
            
            return cleaned_mb
        
        except Exception as e:
            logger.error(f"清理进程工作集失败: {str(e)}")
            return 0
    
    def _trim_processes_individually(self):
        """逐个进程清理工作集（权限要求较低的方法）"""
        logger.debug("使用逐个进程清理模式")
        use_debug_privilege = self.available_functions.get("debug_other_processes", False)
        
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # 根据权限选择打开进程的方式
                if use_debug_privilege:
                    handle = windll.kernel32.OpenProcess(
                        PROCESS_ALL_ACCESS,
                        False,
                        proc.info['pid']
                    )
                else:
                    # 使用较低权限尝试
                    handle = windll.kernel32.OpenProcess(
                        0x0200 | 0x0400, # PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA
                        False,
                        proc.info['pid']
                    )
                    
                    if not handle:
                        # 再次尝试最低权限
                        handle = windll.kernel32.OpenProcess(
                            0x1000 | 0x0400, # PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_SET_QUOTA
                            False,
                            proc.info['pid']
                        )
                
                if handle:
                    windll.psapi.EmptyWorkingSet(handle)
                    windll.kernel32.CloseHandle(handle)
            except Exception:
                # 忽略无法清理的进程
                pass
    
    def flush_system_buffer(self):
        """清理系统缓存"""
        try:
            logger.debug("清理系统缓存")
            
            # 获取清理前的可用内存
            before_available = self._get_memory_before_clean()
            
            # 创建系统文件缓存信息结构
            info = SYSTEM_FILECACHE_INFORMATION()
            info.MinimumWorkingSet = -1
            info.MaximumWorkingSet = -1
            
            # 设置系统信息
            status = self.NtSetSystemInformation(
                SystemFileCacheInformation,
                byref(info),
                sizeof(SYSTEM_FILECACHE_INFORMATION)
            )
            
            if status == 0:
                logger.debug("清理系统缓存API调用成功")
            else:
                logger.warning(f"清理系统缓存API调用失败，错误码: {status}")
            
            # 计算清理的内存量
            after_available = self._get_memory_before_clean()
            cleaned_mb = max(0, (after_available - before_available) / (1024 * 1024))
            self._record_cleaned_memory(cleaned_mb)
            logger.debug(f"清理系统缓存完成，释放了 {cleaned_mb:.2f}MB 内存")
            
            return cleaned_mb
            
        except Exception as e:
            logger.error(f"清理系统缓存失败: {str(e)}")
            return 0
    
    def clean_memory_all(self):
        """全面清理系统内存"""
        try:
            logger.debug("全面清理系统内存")
            
            # 获取清理前的可用内存
            before_available = self._get_memory_before_clean()
            
            # 1. 合并物理内存 (Windows 8+)
            try:
                combine_info = MEMORY_COMBINE_INFORMATION_EX()
                status = self.NtSetSystemInformation(
                    SystemCombinePhysicalMemoryInformation,
                    byref(combine_info),
                    sizeof(MEMORY_COMBINE_INFORMATION_EX)
                )
                if status == 0:
                    logger.debug(f"合并物理内存成功，合并了 {combine_info.PagesCombined} 页")
                else:
                    logger.warning(f"合并物理内存失败，错误码: {status}")
            except Exception as e:
                logger.debug(f"合并物理内存失败 (可能系统版本不支持): {str(e)}")
            
            # 2. 清理系统工作集
            info = SYSTEM_FILECACHE_INFORMATION()
            info.MinimumWorkingSet = -1
            info.MaximumWorkingSet = -1
            status = self.NtSetSystemInformation(
                SystemFileCacheInformation,
                byref(info),
                sizeof(SYSTEM_FILECACHE_INFORMATION)
            )
            if status == 0:
                logger.debug("清理系统工作集成功")
            else:
                logger.warning(f"清理系统工作集失败，错误码: {status}")
            
            # 3. 清理进程工作集
            command = MemoryEmptyWorkingSets
            status = self.NtSetSystemInformation(
                SystemMemoryListInformation,
                byref(wintypes.ULONG(command)),
                sizeof(wintypes.ULONG)
            )
            if status == 0:
                logger.debug("清理进程工作集成功")
            else:
                logger.warning(f"清理进程工作集失败，错误码: {status}")
            
            # 4. 清理低优先级待机列表
            command = MemoryPurgeLowPriorityStandbyList
            status = self.NtSetSystemInformation(
                SystemMemoryListInformation,
                byref(wintypes.ULONG(command)),
                sizeof(wintypes.ULONG)
            )
            if status == 0:
                logger.debug("清理低优先级待机列表成功")
            else:
                logger.warning(f"清理低优先级待机列表失败，错误码: {status}")
            
            # 5. 清理待机列表
            command = MemoryPurgeStandbyList
            status = self.NtSetSystemInformation(
                SystemMemoryListInformation,
                byref(wintypes.ULONG(command)),
                sizeof(wintypes.ULONG)
            )
            if status == 0:
                logger.debug("清理待机列表成功")
            else:
                logger.warning(f"清理待机列表失败，错误码: {status}")
            
            # 6. 清理修改页面列表
            command = MemoryFlushModifiedList
            status = self.NtSetSystemInformation(
                SystemMemoryListInformation,
                byref(wintypes.ULONG(command)),
                sizeof(wintypes.ULONG)
            )
            if status == 0:
                logger.debug("清理修改页面列表成功")
            else:
                logger.warning(f"清理修改页面列表失败，错误码: {status}")
            
            # 计算清理的内存量
            after_available = self._get_memory_before_clean()
            cleaned_mb = max(0, (after_available - before_available) / (1024 * 1024))
            self._record_cleaned_memory(cleaned_mb)
            logger.debug(f"全面清理系统内存完成，释放了 {cleaned_mb:.2f}MB 内存")
            
            return cleaned_mb
            
        except Exception as e:
            logger.error(f"全面清理系统内存失败: {str(e)}")
            return 0
    
    def get_system_cache_info(self):
        """获取系统缓存信息"""
        try:
            info = SYSTEM_FILECACHE_INFORMATION()
            result_length = wintypes.ULONG(0)
            
            status = self.NtQuerySystemInformation(
                SystemFileCacheInformation,
                byref(info),
                sizeof(SYSTEM_FILECACHE_INFORMATION),
                byref(result_length)
            )
            
            if status == 0:  # STATUS_SUCCESS
                return {
                    'current_size': info.CurrentSize,
                    'peak_size': info.PeakSize,
                    'page_fault_count': info.PageFaultCount
                }
            
            return None
        
        except Exception as e:
            logger.error(f"获取系统缓存信息失败: {str(e)}")
            return None
    
    def get_memory_info(self):
        """获取内存使用情况"""
        try:
            mem = psutil.virtual_memory()
            return {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'percent': mem.percent
            }
        except Exception as e:
            logger.error(f"获取内存信息失败: {str(e)}")
            return None
    
    def start_cleaner_thread(self):
        """启动内存清理线程"""
        if self.running:
            logger.debug("内存清理线程已在运行")
            return
        
        # 检查是否有任何清理选项被启用
        if not any(self.clean_switches):
            logger.debug("未启动内存清理线程，因为未启用任何清理选项")
            return
        
        self.running = True
        self._clean_thread = threading.Thread(target=self._cleaner_thread_func, daemon=True)
        self._clean_thread.start()
        logger.debug("内存清理线程已启动")
    
    def stop_cleaner_thread(self):
        """停止内存清理线程"""
        if not self.running:
            return
            
        self.running = False
        
        logger.debug("内存清理线程停止标志已设置，线程将在下次循环时退出")
        
        # 线程是daemon线程，程序退出时会自动结束
    
    def _cleaner_thread_func(self):
        """内存清理线程函数"""
        last_clean_time = time.time()
        
        while self.running:
            try:
                cleaned = False
                current_time = time.time()
                
                # 检查是否有任何清理选项被启用
                any_option_enabled = any(self.clean_switches)
                
                # 只有在至少启用了一个清理选项的情况下才执行清理
                if any_option_enabled:
                    # 定时清理
                    if self.clean_switches[0] or self.clean_switches[1] or self.clean_switches[2]:
                        if current_time - last_clean_time > self.clean_interval:
                            logger.debug(f"定时内存清理触发，距上次清理: {int(current_time - last_clean_time)}秒")
                            
                            # 清理进程工作集
                            if self.clean_switches[0]:
                                self.trim_process_working_set()
                            
                            # 清理系统缓存
                            if self.clean_switches[1]:
                                self.flush_system_buffer()
                            
                            # 全面清理
                            if self.clean_switches[2]:
                                self.clean_memory_all()
                            
                            last_clean_time = current_time
                            cleaned = True
                    
                    # 内存使用率触发清理
                    if (not cleaned and 
                        (self.clean_switches[3] or self.clean_switches[4] or self.clean_switches[5]) and
                        (current_time - self._last_threshold_clean > self.cooldown_time)):  # 确保冷却时间已过
                        
                        mem_info = self.get_memory_info()
                        
                        if mem_info and mem_info['percent'] >= self.threshold:
                            logger.debug(f"内存使用率触发清理，当前使用率: {mem_info['percent']}%，阈值: {self.threshold}%")
                            
                            # 清理进程工作集
                            if self.clean_switches[3]:
                                self.trim_process_working_set()
                            
                            # 清理系统缓存
                            if self.clean_switches[4]:
                                self.flush_system_buffer()
                            
                            # 全面清理
                            if self.clean_switches[5]:
                                self.clean_memory_all()
                            
                            # 更新最后一次基于阈值的清理时间
                            self._last_threshold_clean = current_time
                else:
                    # 没有启用任何清理选项，记录日志并等待
                    if hasattr(self, '_last_no_option_warning') and current_time - self._last_no_option_warning < 60:
                        pass  # 一分钟内不重复记录日志
                    else:
                        logger.debug("内存清理已启用，但未勾选任何清理选项，清理线程处于空闲状态")
                        self._last_no_option_warning = current_time
                
                # 使用短时间的多次休眠替代长时间休眠，以便能更快响应停止命令
                for _ in range(15):
                    if not self.running:
                        break
                    time.sleep(1)
                
            except Exception as e:
                logger.error(f"内存清理线程出现异常: {str(e)}")
                # 出错后延长休眠时间，但也分成短循环以便响应停止
                for _ in range(30):
                    if not self.running:
                        break
                    time.sleep(2)
    
    def manual_clean(self):
        """手动执行内存清理"""
        try:
            logger.debug("执行手动内存清理")
            
            # 清理进程工作集
            self.trim_process_working_set()
            
            # 清理系统缓存
            self.flush_system_buffer()
            
            # 全面清理
            self.clean_memory_all()
            
            return True
        except Exception as e:
            logger.error(f"手动内存清理失败: {str(e)}")
            return False
    
    def set_clean_interval(self, seconds):
        """设置清理间隔时间"""
        # 确保时间不小于60秒
        if seconds < 60:
            seconds = 60
            logger.warning("清理间隔不能小于60秒，已自动调整为60秒")
        
        self.clean_interval = seconds
        logger.debug(f"内存清理间隔已设置为 {seconds} 秒")
        self.sync_to_config_manager()
        return True
    
    def set_memory_threshold(self, percent):
        """设置内存占用触发阈值"""
        # 确保百分比在有效范围内
        if percent < 15:
            percent = 15
            logger.warning("内存占用触发阈值不能小于15%，已自动调整为15%")
        elif percent > 95:
            percent = 95
            logger.warning("内存占用触发阈值不能大于95%，已自动调整为95%")
            
        self.threshold = percent
        logger.debug(f"内存占用触发阈值已设置为 {percent}%")
        self.sync_to_config_manager()
        return True
    
    def set_cooldown_time(self, seconds):
        """设置清理冷却时间"""
        # 确保冷却时间不小于30秒
        if seconds < 30:
            seconds = 30
            logger.warning("清理冷却时间不能小于30秒，已自动调整为30秒")
        
        self.cooldown_time = seconds
        logger.debug(f"内存清理冷却时间已设置为 {seconds} 秒")
        self.sync_to_config_manager()
        return True
    
    def get_clean_stats(self):
        """获取内存清理统计信息"""
        import datetime
        
        last_time_str = "从未清理" if not self.last_clean_time else datetime.datetime.fromtimestamp(
            self.last_clean_time).strftime("%Y-%m-%d %H:%M:%S")
            
        return {
            "total_cleaned_mb": self.total_cleaned_mb,
            "last_cleaned_mb": self.last_cleaned_mb,
            "clean_count": self.clean_count,
            "last_clean_time": last_time_str
        }
    
    def set_clean_option(self, option_index, enabled):
        """设置清理选项状态"""
        if 0 <= option_index < len(self.clean_switches):
            self.clean_switches[option_index] = enabled
            logger.debug(f"内存清理选项 {option_index + 1} 已{'启用' if enabled else '禁用'}")
            
            # 同步到配置
            self.sync_to_config_manager()
            
            # 检查是否需要启动或停止线程
            self._check_should_run_thread()
            
            return True
        return False

# 提供一个获取单例实例的函数
def get_memory_cleaner():
    """获取内存清理管理器实例"""
    return MemoryCleanerManager() 