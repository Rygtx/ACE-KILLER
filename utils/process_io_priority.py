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

class ProcessIoPriorityManager:
    """处理进程I/O优先级管理的类"""
    
    def __init__(self):
        # 加载ntdll.dll
        self.ntdll = ctypes.WinDLL('ntdll.dll')
        self.kernel32 = ctypes.WinDLL('kernel32.dll')
        
        # 定义NtSetInformationProcess函数
        self.NtSetInformationProcess = self.ntdll.NtSetInformationProcess
        self.NtSetInformationProcess.argtypes = [
            wintypes.HANDLE,                 # ProcessHandle
            ctypes.c_int,                    # ProcessInformationClass
            ctypes.c_void_p,                 # ProcessInformation
            ctypes.c_ulong                   # ProcessInformationLength
        ]
        self.NtSetInformationProcess.restype = ctypes.c_ulong
    
    def set_process_io_priority(self, process_id, priority=IO_PRIORITY_HINT.IoPriorityVeryLow):
        """
        设置指定进程的I/O优先级
        
        Args:
            process_id: 进程ID
            priority: I/O优先级，默认为最低优先级
            
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
                logger.error(f"无法打开进程(PID={process_id})，错误码: {ctypes.GetLastError()}")
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
                logger.error(f"设置进程(PID={process_id})I/O优先级失败，NTSTATUS: 0x{status:08x}")
                return False
            
            logger.debug(f"成功设置进程(PID={process_id})的I/O优先级为: {priority}")
            return True
            
        except Exception as e:
            logger.error(f"设置进程I/O优先级时发生错误: {str(e)}")
            return False
    
    def set_process_io_priority_by_name(self, process_name, priority=IO_PRIORITY_HINT.IoPriorityVeryLow):
        """
        通过进程名称设置所有匹配进程的I/O优先级
        
        Args:
            process_name: 进程名称
            priority: I/O优先级，默认为最低优先级
            
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
                    if self.set_process_io_priority(proc.info['pid'], priority):
                        success_count += 1
            
            if total_count == 0:
                logger.warning(f"未找到名为 {process_name} 的进程")
            else:
                logger.debug(f"已为 {success_count}/{total_count} 个名为 {process_name} 的进程设置I/O优先级")
            
            return (success_count, total_count)
            
        except Exception as e:
            logger.error(f"通过名称设置进程I/O优先级时发生错误: {str(e)}")
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
            
            success, count = self.io_manager.set_process_io_priority_by_name(process_name, priority)
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