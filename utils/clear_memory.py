#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes
import os
import platform
import psutil
import subprocess
import time
from loguru import logger


class MemoryCleaner:
    """
    内存清理工具类，用于清理系统内存占用以提升游戏帧数
    """
    def __init__(self):
        """
        初始化内存清理器
        """
        self.last_clean_time = 0
        self.clean_interval = 300  # 默认清理间隔为5分钟
        self.min_threshold = 30  # 默认内存使用率阈值，低于此值不清理
        self.is_admin = self._is_admin()
        
        # 记录初始化信息
        logger.info("内存清理模块初始化完成")
        logger.info(f"管理员权限状态: {'已获取' if self.is_admin else '未获取'}")
    
    def _is_admin(self):
        """
        检查当前程序是否以管理员权限运行
        
        Returns:
            bool: 是否拥有管理员权限
        """
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception as e:
            logger.error(f"检查管理员权限失败: {str(e)}")
            return False
    
    def get_memory_usage(self):
        """
        获取当前系统内存使用情况
        
        Returns:
            tuple: (已用内存百分比, 总内存大小(GB), 已用内存大小(GB), 可用内存大小(GB))
        """
        try:
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024**3)
            used_gb = memory.used / (1024**3)
            available_gb = memory.available / (1024**3)
            percent = memory.percent
            
            return percent, total_gb, used_gb, available_gb
        except Exception as e:
            logger.error(f"获取内存使用情况失败: {str(e)}")
            return 0, 0, 0, 0
    
    def clear_system_cache(self):
        """
        清理系统缓存
        
        Returns:
            bool: 清理是否成功
        """
        try:
            logger.info("开始清理系统缓存")
            success_count = 0
            
            # 1. 清理当前进程工作集
            try:
                # 使用Windows API清理工作集
                ctypes.windll.psapi.EmptyWorkingSet(ctypes.c_int(-1))
                success_count += 1
                logger.debug("成功清理当前进程工作集")
            except Exception as e:
                logger.warning(f"清理当前进程工作集失败: {str(e)}")
            
            # 2. 使用SetProcessWorkingSetSize API清理所有进程内存
            try:
                kernel32 = ctypes.WinDLL('kernel32.dll')
                
                # 设置函数参数类型
                kernel32.SetProcessWorkingSetSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
                kernel32.SetProcessWorkingSetSize.restype = ctypes.c_int
                kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
                kernel32.OpenProcess.restype = ctypes.c_void_p
                kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
                kernel32.CloseHandle.restype = ctypes.c_int
                
                # 获取当前进程句柄
                current_process = kernel32.GetCurrentProcess()
                
                # 清理当前进程工作集
                result = kernel32.SetProcessWorkingSetSize(current_process, -1, -1)
                if result != 0:
                    success_count += 1
                    logger.debug("成功清理当前进程工作集")
                else:
                    logger.warning("清理当前进程工作集失败")
                
                # 定义进程访问权限
                PROCESS_SET_QUOTA = 0x0100
                PROCESS_TERMINATE = 0x0001
                PROCESS_QUERY_INFORMATION = 0x0400
                
                # 清理其他进程的工作集
                cleaned_processes = 0
                skipped_processes = 0
                
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        # 跳过系统关键进程
                        if proc.info['name'].lower() in [
                            'system', 'smss.exe', 'csrss.exe', 'wininit.exe',
                            'services.exe', 'lsass.exe', 'winlogon.exe'
                        ]:
                            skipped_processes += 1
                            continue
                        
                        # 跳过当前进程
                        if proc.pid == os.getpid():
                            continue
                        
                        # 打开进程
                        hProcess = kernel32.OpenProcess(
                            PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION,
                            False,
                            proc.pid
                        )
                        
                        if hProcess:
                            # 设置工作集大小为最小值
                            result = kernel32.SetProcessWorkingSetSize(hProcess, -1, -1)
                            kernel32.CloseHandle(hProcess)
                            if result != 0:
                                cleaned_processes += 1
                    except:
                        pass
                
                logger.info(f"成功清理 {cleaned_processes} 个进程的工作集，跳过 {skipped_processes} 个系统进程")
                if cleaned_processes > 0:
                    success_count += 1
            except Exception as e:
                logger.warning(f"清理进程工作集失败: {str(e)}")
            
            # 3. 使用全局内存状态API
            try:
                kernel32 = ctypes.WinDLL('kernel32.dll')
                
                # 定义内存状态结构体
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong),
                        ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong),
                        ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong),
                        ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                    ]
                
                # 初始化结构体
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(stat)
                
                # 获取内存状态
                kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                logger.debug(f"内存使用率: {stat.dwMemoryLoad}%, 物理内存: 总计 {stat.ullTotalPhys/(1024**3):.2f}GB, 可用 {stat.ullAvailPhys/(1024**3):.2f}GB")
                success_count += 1
            except Exception as e:
                logger.warning(f"获取内存状态失败: {str(e)}")
            
            # 4. 尝试使用GC回收Python对象
            try:
                import gc
                gc.collect()
                success_count += 1
                logger.debug("成功执行Python垃圾回收")
            except Exception as e:
                logger.warning(f"执行Python垃圾回收失败: {str(e)}")
            
            # 判断整体清理是否成功
            if success_count > 0:
                logger.info(f"系统缓存清理完成，成功执行了 {success_count} 种清理方法")
                return True
            else:
                logger.warning("所有清理方法均失败")
                return False
            
        except Exception as e:
            logger.error(f"清理系统缓存失败: {str(e)}")
            return False
    
    def optimize_processes(self):
        """
        优化系统进程，降低非关键进程的优先级
        
        Returns:
            int: 优化的进程数量
        """
        try:
            count = 0
            # 获取所有进程
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    # 跳过系统关键进程
                    if proc.info['name'].lower() in [
                        'system', 'svchost.exe', 'csrss.exe', 'wininit.exe',
                        'services.exe', 'lsass.exe', 'winlogon.exe', 'explorer.exe'
                    ]:
                        continue
                    
                    # 跳过当前进程
                    if proc.pid == os.getpid():
                        continue
                    
                    # 获取进程对象
                    process = psutil.Process(proc.pid)
                    
                    # 检查当前优先级
                    if process.nice() <= 32:  # 正常或更高优先级
                        # 设置为低优先级
                        process.nice(64)  # BELOW_NORMAL_PRIORITY_CLASS
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
                except Exception as e:
                    logger.debug(f"优化进程 {proc.info['name']} 失败: {str(e)}")
            
            return count
        except Exception as e:
            logger.error(f"优化系统进程失败: {str(e)}")
            return 0
    
    def trim_process_working_sets(self):
        """
        压缩所有进程的工作集
        
        Returns:
            int: 处理的进程数量
        """
        try:
            count = 0
            # 获取所有进程
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    # 跳过系统进程
                    if proc.info['name'].lower() in ['system']:
                        continue
                    
                    # 使用Windows API压缩工作集
                    handle = ctypes.windll.kernel32.OpenProcess(0x1F0FFF, False, proc.pid)
                    if handle:
                        result = ctypes.windll.psapi.EmptyWorkingSet(handle)
                        ctypes.windll.kernel32.CloseHandle(handle)
                        if result:
                            count += 1
                except Exception as e:
                    logger.debug(f"压缩进程 {proc.info['name']} 工作集失败: {str(e)}")
            
            return count
        except Exception as e:
            logger.error(f"压缩进程工作集失败: {str(e)}")
            return 0
    
    def clean_memory(self, force=False):
        """
        执行内存清理操作
        
        Args:
            force (bool): 是否强制清理，忽略时间间隔和内存阈值
            
        Returns:
            dict: 清理结果信息
        """
        current_time = time.time()
        
        # 检查清理间隔
        if not force and (current_time - self.last_clean_time) < self.clean_interval:
            return {
                "success": False,
                "message": f"清理间隔未到，距离上次清理已过 {int(current_time - self.last_clean_time)} 秒，需要 {self.clean_interval} 秒",
                "memory_before": None,
                "memory_after": None
            }
        
        # 获取清理前内存使用情况
        before_percent, before_total, before_used, before_available = self.get_memory_usage()
        
        # 检查内存使用阈值
        if not force and before_percent < self.min_threshold:
            return {
                "success": False,
                "message": f"内存使用率 {before_percent:.1f}% 低于阈值 {self.min_threshold}%，无需清理",
                "memory_before": {
                    "percent": before_percent,
                    "total_gb": before_total,
                    "used_gb": before_used,
                    "available_gb": before_available
                },
                "memory_after": None
            }
        
        logger.info(f"开始清理内存，当前使用率: {before_percent:.1f}%")
        
        # 执行清理操作
        cache_result = self.clear_system_cache()
        process_count = self.trim_process_working_sets()
        optimize_count = self.optimize_processes()
        
        # 更新最后清理时间
        self.last_clean_time = current_time
        
        # 获取清理后内存使用情况
        after_percent, after_total, after_used, after_available = self.get_memory_usage()
        
        # 计算清理效果
        freed_memory = before_used - after_used
        percent_change = before_percent - after_percent
        
        result = {
            "success": True,
            "message": f"内存清理完成，释放了 {freed_memory:.2f}GB 内存，使用率下降 {percent_change:.1f}%",
            "details": {
                "cache_cleared": cache_result,
                "processes_trimmed": process_count,
                "processes_optimized": optimize_count
            },
            "memory_before": {
                "percent": before_percent,
                "total_gb": before_total,
                "used_gb": before_used,
                "available_gb": before_available
            },
            "memory_after": {
                "percent": after_percent,
                "total_gb": after_total,
                "used_gb": after_used,
                "available_gb": after_available
            }
        }
        
        logger.info(f"内存清理完成，释放了 {freed_memory:.2f}GB 内存，使用率从 {before_percent:.1f}% 降至 {after_percent:.1f}%")
        
        return result
    
    def set_clean_interval(self, seconds):
        """
        设置清理间隔时间
        
        Args:
            seconds (int): 清理间隔秒数
            
        Returns:
            bool: 设置是否成功
        """
        try:
            if seconds < 10:
                logger.warning(f"清理间隔时间 {seconds} 秒过短，已设置为最小值 10 秒")
                seconds = 10
            
            self.clean_interval = seconds
            logger.info(f"清理间隔时间已设置为 {seconds} 秒")
            return True
        except Exception as e:
            logger.error(f"设置清理间隔时间失败: {str(e)}")
            return False
    
    def set_memory_threshold(self, percent):
        """
        设置内存使用率阈值
        
        Args:
            percent (int): 内存使用率阈值百分比
            
        Returns:
            bool: 设置是否成功
        """
        try:
            if percent < 10:
                logger.warning(f"内存使用率阈值 {percent}% 过低，已设置为最小值 10%")
                percent = 10
            elif percent > 90:
                logger.warning(f"内存使用率阈值 {percent}% 过高，已设置为最大值 90%")
                percent = 90
            
            self.min_threshold = percent
            logger.info(f"内存使用率阈值已设置为 {percent}%")
            return True
        except Exception as e:
            logger.error(f"设置内存使用率阈值失败: {str(e)}")
            return False


# 单例模式，提供全局访问点
_memory_cleaner_instance = None

def get_memory_cleaner():
    """
    获取内存清理器实例（单例模式）
    
    Returns:
        MemoryCleaner: 内存清理器实例
    """
    global _memory_cleaner_instance
    if _memory_cleaner_instance is None:
        _memory_cleaner_instance = MemoryCleaner()
    return _memory_cleaner_instance


# 测试代码
if __name__ == "__main__":
    # 配置日志
    logger.add("memory_cleaner.log", rotation="10 MB", retention="3 days", level="INFO")
    
    cleaner = get_memory_cleaner()
    
    # 获取当前内存使用情况
    percent, total, used, available = cleaner.get_memory_usage()
    print(f"当前内存使用情况:")
    print(f"  总内存: {total:.2f} GB")
    print(f"  已用内存: {used:.2f} GB ({percent:.1f}%)")
    print(f"  可用内存: {available:.2f} GB")
    
    # 执行内存清理
    result = cleaner.clean_memory(force=True)
    
    if result["success"]:
        print(f"\n清理结果: {result['message']}")
        print(f"处理的进程数: {result['details']['processes_trimmed']}")
        print(f"优化的进程数: {result['details']['processes_optimized']}")
        
        # 显示清理前后对比
        before = result["memory_before"]
        after = result["memory_after"]
        print(f"\n清理前后对比:")
        print(f"  使用率: {before['percent']:.1f}% -> {after['percent']:.1f}% (减少 {before['percent']-after['percent']:.1f}%)")
        print(f"  已用内存: {before['used_gb']:.2f} GB -> {after['used_gb']:.2f} GB (释放 {before['used_gb']-after['used_gb']:.2f} GB)")
        print(f"  可用内存: {before['available_gb']:.2f} GB -> {after['available_gb']:.2f} GB (增加 {after['available_gb']-before['available_gb']:.2f} GB)")
    else:
        print(f"\n清理未执行: {result['message']}")
