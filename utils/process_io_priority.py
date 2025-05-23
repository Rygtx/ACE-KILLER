#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
进程I/O优先级设置模块
"""

import ctypes
import time
import threading
from ctypes import wintypes
import psutil
from loguru import logger
from win32api import OpenProcess
from win32con import PROCESS_ALL_ACCESS
from win32process import (
    SetPriorityClass, 
    IDLE_PRIORITY_CLASS, 
    BELOW_NORMAL_PRIORITY_CLASS, 
    ABOVE_NORMAL_PRIORITY_CLASS,
    NORMAL_PRIORITY_CLASS,
    HIGH_PRIORITY_CLASS,
    REALTIME_PRIORITY_CLASS
)

# 导入权限管理器
from utils.privilege_manager import get_privilege_manager

# Windows API 常量
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_ALL_ACCESS = 0x1F0FFF

# ProcessIoPriority 的枚举值
class IO_PRIORITY_HINT(object):
    IoPriorityVeryLow = 0    # 最低优先级
    IoPriorityLow = 1        # 低优先级
    IoPriorityNormal = 2     # 正常优先级(默认)
    IoPriorityCritical = 3   # 关键优先级

# ProcessInformationClass 枚举
ProcessIoPriority = 33

# 效能模式相关常量
PROCESS_POWER_THROTTLING_INFORMATION = 4
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1
POWER_THROTTLING_PROCESS_ENABLE = 0x1
POWER_THROTTLING_PROCESS_DISABLE = 0x2

# 性能模式枚举 - 增强版本
class PERFORMANCE_MODE(object):
    ECO_MODE = 0              # 效能模式（最低性能，节约功耗）
    NORMAL_MODE = 1           # 正常模式（系统默认）
    HIGH_PERFORMANCE = 2      # 高性能模式（高优先级）
    MAXIMUM_PERFORMANCE = 3   # 最大性能模式（实时优先级，慎用）

# CPU优先级映射
CPU_PRIORITY_MAP = {
    PERFORMANCE_MODE.ECO_MODE: IDLE_PRIORITY_CLASS,
    PERFORMANCE_MODE.NORMAL_MODE: NORMAL_PRIORITY_CLASS,
    PERFORMANCE_MODE.HIGH_PERFORMANCE: HIGH_PRIORITY_CLASS,
    PERFORMANCE_MODE.MAXIMUM_PERFORMANCE: REALTIME_PRIORITY_CLASS
}

class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.DWORD),
        ("ControlMask", wintypes.DWORD),
        ("StateMask", wintypes.DWORD)
    ]

class ProcessIoPriorityManager:
    """处理进程I/O优先级管理的类"""
    
    def __init__(self):
        # 加载ntdll.dll
        self.ntdll = ctypes.WinDLL('ntdll.dll')
        self.kernel32 = ctypes.WinDLL('kernel32.dll')
        
        # 获取权限管理器
        self.privilege_manager = get_privilege_manager()
        
        # 检查是否有必要的权限
        self._check_privileges()
        
        # 定义NtSetInformationProcess函数
        self.NtSetInformationProcess = self.ntdll.NtSetInformationProcess
        self.NtSetInformationProcess.argtypes = [
            wintypes.HANDLE,                 # ProcessHandle
            ctypes.c_int,                    # ProcessInformationClass
            ctypes.c_void_p,                 # ProcessInformation
            ctypes.c_ulong                   # ProcessInformationLength
        ]
        self.NtSetInformationProcess.restype = ctypes.c_ulong
    
    def _check_privileges(self):
        """检查并记录权限状态"""
        # 记录详细的权限状态
        self.privilege_manager.log_privilege_status()
        
        if not self.privilege_manager.has_privilege("set_process_io_priority"):
            logger.warning("缺少设置进程I/O优先级的权限，某些操作可能失败")
            if not self.privilege_manager.check_admin_rights():
                logger.warning("建议以管理员身份运行程序以获得完整的进程管理权限")
        
        if not self.privilege_manager.has_privilege("debug_other_processes"):
            logger.debug("缺少调试权限，无法访问某些受保护的系统进程")
    
    def set_process_io_priority(self, process_id, priority=IO_PRIORITY_HINT.IoPriorityVeryLow, performance_mode=PERFORMANCE_MODE.ECO_MODE):
        """
        设置指定进程的完整优化（I/O优先级 + CPU优先级 + 性能模式）
        
        Args:
            process_id: 进程ID
            priority: I/O优先级，默认为最低优先级
            performance_mode: 性能模式（ECO_MODE=效能模式, NORMAL_MODE=正常模式, HIGH_PERFORMANCE=高性能模式）
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 检查权限
            if not self.privilege_manager.has_privilege("set_process_io_priority"):
                logger.warning(f"缺少设置进程I/O优先级的权限，但仍尝试操作进程(PID={process_id})")
            
            # 第一步：设置I/O优先级
            io_success = self._set_io_priority_only(process_id, priority)
            if not io_success:
                logger.error(f"设置进程(PID={process_id})I/O优先级失败")
                return False
            
            # 第二步：根据性能模式设置CPU优先级
            cpu_success = self._set_cpu_priority_by_mode(process_id, performance_mode)
            
            if not cpu_success:
                logger.warning(f"设置进程(PID={process_id})CPU优先级失败，但I/O优先级设置成功")
            
            # 第三步：根据性能模式设置CPU亲和性
            if performance_mode in [PERFORMANCE_MODE.HIGH_PERFORMANCE, PERFORMANCE_MODE.MAXIMUM_PERFORMANCE]:
                # 高性能模式：允许使用所有CPU核心
                affinity_success = self._set_full_cpu_affinity(process_id)
            else:
                # 效能/正常模式：限制到单个核心（效能模式）或保持默认（正常模式）
                if performance_mode == PERFORMANCE_MODE.ECO_MODE:
                    affinity_success = self._set_cpu_affinity(process_id)
                else:  # NORMAL_MODE
                    affinity_success = True  # 正常模式不修改CPU亲和性
            
            if not affinity_success:
                logger.warning(f"设置进程(PID={process_id})CPU亲和性失败，但其他设置成功")
            
            # 第四步：设置性能模式
            power_success = self._set_process_performance_mode(process_id, performance_mode)
            if not power_success:
                logger.warning(f"设置进程(PID={process_id})性能模式失败，但其他设置成功")
            
            # 只要I/O优先级设置成功就算成功
            mode_text = self._get_performance_mode_text(performance_mode)
            logger.debug(f"进程优化完成(PID={process_id}): I/O={io_success}, CPU={cpu_success}, 亲和性={affinity_success}, 性能模式={power_success} ({mode_text})")
            return True
            
        except Exception as e:
            logger.error(f"设置进程优化时发生错误: {str(e)}")
            return False
    
    def _get_ntstatus_message(self, status_code):
        """获取NTSTATUS错误码的说明"""
        ntstatus_messages = {
            0x00000000: "STATUS_SUCCESS - 操作成功",
            0xC0000061: "STATUS_PRIVILEGE_NOT_HELD - 权限不足，需要管理员权限或特殊权限",
            0xC0000005: "STATUS_ACCESS_DENIED - 访问被拒绝",
            0xC0000008: "STATUS_INVALID_HANDLE - 无效的句柄",
            0xC000000D: "STATUS_INVALID_PARAMETER - 无效的参数",
            0xC0000022: "STATUS_ACCESS_DENIED - 访问被拒绝",
            0xC000007C: "STATUS_INVALID_PARAMETER_1 - 第一个参数无效",
            0xC000007D: "STATUS_INVALID_PARAMETER_2 - 第二个参数无效",
        }
        
        return ntstatus_messages.get(status_code, f"未知错误码: 0x{status_code:08x}")
    
    def _set_io_priority_only(self, process_id, priority):
        """
        仅设置I/O优先级
        
        Args:
            process_id: 进程ID
            priority: I/O优先级
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 打开进程
            process_handle = self.kernel32.OpenProcess(
                PROCESS_SET_INFORMATION | PROCESS_QUERY_INFORMATION,
                False,
                process_id
            )
            
            if not process_handle:
                error_code = ctypes.GetLastError()
                logger.error(f"无法打开进程(PID={process_id})，错误码: {error_code}")
                
                # 提供具体的错误解释
                if error_code == 5:  # ERROR_ACCESS_DENIED
                    logger.error(f"进程(PID={process_id})访问被拒绝，可能是系统进程或权限不足")
                    if not self.privilege_manager.check_admin_rights():
                        logger.error("建议以管理员身份运行程序")
                elif error_code == 87:  # ERROR_INVALID_PARAMETER
                    logger.error(f"进程(PID={process_id})可能已经退出")
                
                return False
            
            # 分配内存并设置优先级值
            priority_value = ctypes.c_int(priority)
            
            # 调用NtSetInformationProcess设置I/O优先级
            status = self.NtSetInformationProcess(
                process_handle,              # 进程句柄
                ProcessIoPriority,           # ProcessInformationClass
                ctypes.byref(priority_value),# 优先级值指针
                ctypes.sizeof(priority_value)# 大小
            )
            
            # 关闭进程句柄
            self.kernel32.CloseHandle(process_handle)
            
            if status != 0:
                error_message = self._get_ntstatus_message(status)
                logger.error(f"设置进程(PID={process_id})I/O优先级失败，{error_message}")
                
                # 特殊处理权限不足的情况
                if status == 0xC0000061:  # STATUS_PRIVILEGE_NOT_HELD
                    logger.error(f"进程(PID={process_id})I/O优先级设置需要更高权限")
                    if not self.privilege_manager.check_admin_rights():
                        logger.error("请以管理员身份运行程序，或者该进程受系统保护无法修改")
                    else:
                        logger.error("即使是管理员权限也无法修改此进程，可能是受保护的系统进程")
                
                return False
            
            logger.debug(f"成功设置进程(PID={process_id})的I/O优先级为: {priority}")
            return True
            
        except Exception as e:
            logger.error(f"设置I/O优先级时发生错误: {str(e)}")
            return False
    
    def _set_cpu_priority_by_mode(self, process_id, performance_mode):
        """
        根据性能模式设置CPU优先级
        
        Args:
            process_id: 进程ID
            performance_mode: 性能模式
            
        Returns:
            bool: 操作是否成功
        """
        try:
            # 正常模式不修改CPU优先级
            if performance_mode == PERFORMANCE_MODE.NORMAL_MODE:
                logger.debug(f"进程(PID={process_id})保持系统默认CPU优先级")
                return True
            
            # 使用win32api打开进程
            handle = OpenProcess(PROCESS_ALL_ACCESS, False, process_id)
            if not handle:
                logger.error(f"无法打开进程(PID={process_id})用于设置CPU优先级")
                return False
            
            # 根据性能模式获取对应的优先级
            priority_class = CPU_PRIORITY_MAP.get(performance_mode, NORMAL_PRIORITY_CLASS)
            
            # 实时优先级需要特别警告
            if performance_mode == PERFORMANCE_MODE.MAXIMUM_PERFORMANCE:
                logger.warning(f"正在为进程(PID={process_id})设置实时优先级，这可能影响系统稳定性")
            
            # 设置CPU优先级
            SetPriorityClass(handle, priority_class)
            
            # 关闭句柄
            import win32api
            win32api.CloseHandle(handle)
            
            # 记录优化级别
            priority_names = {
                IDLE_PRIORITY_CLASS: "低优先级(IDLE)",
                BELOW_NORMAL_PRIORITY_CLASS: "低于正常",
                NORMAL_PRIORITY_CLASS: "正常优先级",
                ABOVE_NORMAL_PRIORITY_CLASS: "高于正常",
                HIGH_PRIORITY_CLASS: "高优先级",
                REALTIME_PRIORITY_CLASS: "实时优先级"
            }
            
            priority_name = priority_names.get(priority_class, f"未知({priority_class})")
            logger.debug(f"成功设置进程(PID={process_id})的CPU优先级为: {priority_name}")
            return True
            
        except Exception as e:
            logger.error(f"设置CPU优先级时发生错误: {str(e)}")
            return False
    
    def _set_cpu_affinity(self, process_id):
        """
        设置CPU亲和性到最后一个核心
        
        Args:
            process_id: 进程ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            proc = psutil.Process(process_id)
            cores = psutil.cpu_count(logical=True)
            if cores > 1:
                # 设置到最后一个核心
                small_core = cores - 1
                proc.cpu_affinity([small_core])
                logger.debug(f"成功设置进程(PID={process_id})的CPU亲和性到核心{small_core}")
                return True
            else:
                logger.debug(f"系统只有一个核心，跳过CPU亲和性设置(PID={process_id})")
                return True
                
        except Exception as e:
            logger.error(f"设置CPU亲和性时发生错误: {str(e)}")
            return False
    
    def _set_full_cpu_affinity(self, process_id):
        """
        设置CPU亲和性为所有核心（用于高性能模式）
        
        Args:
            process_id: 进程ID
            
        Returns:
            bool: 操作是否成功
        """
        try:
            proc = psutil.Process(process_id)
            cores = psutil.cpu_count(logical=True)
            if cores > 1:
                # 设置使用所有CPU核心
                all_cores = list(range(cores))
                proc.cpu_affinity(all_cores)
                logger.debug(f"成功设置进程(PID={process_id})的CPU亲和性到所有核心: {all_cores}")
                return True
            else:
                logger.debug(f"系统只有一个核心，无需设置CPU亲和性(PID={process_id})")
                return True
                
        except Exception as e:
            logger.error(f"设置完整CPU亲和性时发生错误: {str(e)}")
            return False
    
    def _set_process_performance_mode(self, process_id, performance_mode):
        """
        设置进程的性能模式
        
        Args:
            process_id: 进程ID
            performance_mode: 性能模式（ECO_MODE, NORMAL_MODE, HIGH_PERFORMANCE）
            
        Returns:
            bool: 是否成功设置
        """
        try:
            # 获取SetProcessInformation函数
            SetProcessInformation = ctypes.windll.kernel32.SetProcessInformation
            
            # 打开进程
            process_handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_ALL_ACCESS, False, process_id
            )
            
            if not process_handle:
                logger.error(f"无法打开进程(PID={process_id})句柄用于设置性能模式")
                return False
            
            # 创建并初始化PROCESS_POWER_THROTTLING_STATE结构体
            throttling_state = PROCESS_POWER_THROTTLING_STATE()
            throttling_state.Version = 1
            throttling_state.ControlMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
            
            # 根据性能模式设置StateMask
            if performance_mode == PERFORMANCE_MODE.ECO_MODE:
                # 效能模式：启用节流，降低性能和功耗
                throttling_state.StateMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
                mode_text = "效能模式"
            elif performance_mode in [PERFORMANCE_MODE.HIGH_PERFORMANCE, PERFORMANCE_MODE.MAXIMUM_PERFORMANCE]:
                # 高性能/最大性能模式：禁用节流，提升性能优先级
                throttling_state.StateMask = 0  # 不启用节流
                mode_text = "高性能模式" if performance_mode == PERFORMANCE_MODE.HIGH_PERFORMANCE else "最大性能模式"
            else:  # NORMAL_MODE
                # 正常模式：使用系统默认设置
                # 这里我们不调用SetProcessInformation，让系统保持默认
                ctypes.windll.kernel32.CloseHandle(process_handle)
                logger.debug(f"进程(PID={process_id})保持系统默认性能模式")
                return True
            
            # 调用SetProcessInformation设置性能模式
            result = SetProcessInformation(
                process_handle,
                PROCESS_POWER_THROTTLING_INFORMATION,
                ctypes.byref(throttling_state),
                ctypes.sizeof(throttling_state)
            )
            
            # 关闭进程句柄
            ctypes.windll.kernel32.CloseHandle(process_handle)
            
            if result:
                logger.debug(f"成功将进程(PID={process_id})设置为{mode_text}")
                return True
            else:
                error = ctypes.windll.kernel32.GetLastError()
                logger.error(f"设置进程性能模式失败，错误码: {error}")
                return False
        except Exception as e:
            logger.error(f"设置进程性能模式时发生异常: {str(e)}")
            return False
    
    def _get_performance_mode_text(self, performance_mode):
        """
        获取性能模式的文本描述
        
        Args:
            performance_mode: 性能模式
            
        Returns:
            str: 性能模式的文本描述
        """
        mode_map = {
            PERFORMANCE_MODE.ECO_MODE: "效能模式",
            PERFORMANCE_MODE.NORMAL_MODE: "正常模式", 
            PERFORMANCE_MODE.HIGH_PERFORMANCE: "高性能模式",
            PERFORMANCE_MODE.MAXIMUM_PERFORMANCE: "最大性能模式"
        }
        return mode_map.get(performance_mode, f"未知模式({performance_mode})")
    
    def _set_process_eco_qos(self, process_id):
        """
        设置进程为效能模式 (EcoQoS) - 保持向后兼容
        
        Args:
            process_id: 进程ID
            
        Returns:
            bool: 是否成功设置
        """
        return self._set_process_performance_mode(process_id, PERFORMANCE_MODE.ECO_MODE)
    
    def set_process_io_priority_by_name(self, process_name, priority=IO_PRIORITY_HINT.IoPriorityVeryLow, performance_mode=PERFORMANCE_MODE.ECO_MODE):
        """
        通过进程名称设置所有匹配进程的完整优化
        
        Args:
            process_name: 进程名称
            priority: I/O优先级，默认为最低优先级
            performance_mode: 性能模式（ECO_MODE=效能模式, NORMAL_MODE=正常模式, HIGH_PERFORMANCE=高性能模式）
            
        Returns:
            tuple: (成功设置的进程数, 总尝试的进程数)
        """
        success_count = 0
        total_count = 0
        
        try:
            # 查找所有匹配的进程
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    total_count += 1
                    if self.set_process_io_priority(proc.info['pid'], priority, performance_mode):
                        success_count += 1
            
            if total_count == 0:
                logger.warning(f"未找到名为 {process_name} 的进程")
            else:
                mode_text = self._get_performance_mode_text(performance_mode)
                logger.debug(f"已为 {success_count}/{total_count} 个名为 {process_name} 的进程设置优化 ({mode_text})")
            
            return (success_count, total_count)
            
        except Exception as e:
            logger.error(f"通过名称设置进程优化时发生错误: {str(e)}")
            return (success_count, total_count)
    
    def get_process_info(self, process_id):
        """
        获取进程信息
        
        Args:
            process_id: 进程ID
            
        Returns:
            dict: 进程信息或None
        """
        try:
            proc = psutil.Process(process_id)
            return {
                'pid': proc.pid,
                'name': proc.name(),
                'create_time': proc.create_time(),
                'cpu_percent': proc.cpu_percent(interval=0.1),
                'memory_percent': proc.memory_percent(),
                'status': proc.status()
            }
        except Exception as e:
            logger.error(f"获取进程信息失败, PID={process_id}: {str(e)}")
            return None


class ProcessIoPriorityService:
    """自动设置进程I/O优先级的服务类"""
    
    def __init__(self, config_manager):
        """初始化I/O优先级服务"""
        self.config_manager = config_manager
        self.io_manager = get_io_priority_manager()
        self.running = False
        self.thread = None
        self.check_interval = 30  # 检查间隔，单位秒
        self.auto_optimize_enabled = True  # 自动优化开关
    
    def start_service(self):
        """启动I/O优先级服务"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._service_loop, daemon=True)
            self.thread.start()
            logger.debug("I/O优先级服务已启动")
            return True
        return False
    
    def stop_service(self):
        """停止I/O优先级服务"""
        if self.running:
            self.running = False
            logger.debug("I/O优先级服务正在停止...")
            if self.thread and self.thread.is_alive():
                self.thread.join(2.0)  # 等待最多2秒
            logger.debug("I/O优先级服务已停止")
            return True
        return False
    
    def _service_loop(self):
        """服务主循环"""
        while self.running:
            try:
                if self.auto_optimize_enabled:
                    self._check_and_set_processes()
            except Exception as e:
                logger.error(f"I/O优先级服务出错: {str(e)}")
            
            # 睡眠一段时间
            for _ in range(self.check_interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def _check_and_set_processes(self):
        """检查并设置指定进程的I/O优先级"""
        processes_to_optimize = self.config_manager.io_priority_processes
        if not processes_to_optimize:
            return
        
        total_processes = 0
        successful_processes = 0
        
        for proc_config in processes_to_optimize:
            if not isinstance(proc_config, dict) or 'name' not in proc_config:
                continue
            
            process_name = proc_config['name']
            priority = proc_config.get('priority', IO_PRIORITY_HINT.IoPriorityVeryLow)
            performance_mode = proc_config.get('performance_mode', PERFORMANCE_MODE.ECO_MODE)
            
            success, count = self.io_manager.set_process_io_priority_by_name(process_name, priority, performance_mode)
            total_processes += count
            successful_processes += success
        
        if total_processes > 0:
            logger.debug(f"自动优化完成: 已处理 {successful_processes}/{total_processes} 个进程")


# 单例模式获取ProcessIoPriorityManager实例
_io_priority_manager = None
_io_priority_service = None

def get_io_priority_manager():
    """获取ProcessIoPriorityManager单例"""
    global _io_priority_manager
    if _io_priority_manager is None:
        _io_priority_manager = ProcessIoPriorityManager()
    return _io_priority_manager

def get_io_priority_service(config_manager=None):
    """获取ProcessIoPriorityService单例"""
    global _io_priority_service
    if _io_priority_service is None and config_manager is not None:
        _io_priority_service = ProcessIoPriorityService(config_manager)
    return _io_priority_service 