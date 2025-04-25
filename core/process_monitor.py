#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
进程监控核心模块
"""

import os
import queue
import threading
import time
import psutil
from loguru import logger
from win32api import OpenProcess
from win32con import PROCESS_ALL_ACCESS
from win32process import SetPriorityClass, IDLE_PRIORITY_CLASS, BELOW_NORMAL_PRIORITY_CLASS
import ctypes
from ctypes import wintypes

# 定义Windows API常量和结构体
PROCESS_POWER_THROTTLING_INFORMATION = 4
PROCESS_POWER_THROTTLING_EXECUTION_SPEED = 0x1
POWER_THROTTLING_PROCESS_ENABLE = 0x1
POWER_THROTTLING_PROCESS_DISABLE = 0x2

class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.DWORD),
        ("ControlMask", wintypes.DWORD),
        ("StateMask", wintypes.DWORD)
    ]


class GameProcessMonitor:
    """游戏进程监控类"""
    
    def __init__(self, config_manager):
        """
        初始化游戏进程监控器
        
        Args:
            config_manager: 配置管理器对象
        """
        self.config_manager = config_manager
        self.anticheat_name = "ACE-Tray.exe"  # 反作弊进程名称
        self.scanprocess_name = "SGuard64.exe"  # 扫描进程名称
        self.running = False  # 监控线程运行标记，初始为False
        self.main_game_running = False  # 游戏主进程是否运行中标记
        self.process_cache = {}  # 进程缓存
        self.cache_timeout = 5  # 缓存超时时间（秒）
        self.last_cache_refresh = 0  # 上次缓存刷新时间
        self.anticheat_killed = False  # 终止ACE进程标记
        self.scanprocess_optimized = False  # 优化SGuard64进程标记
        self.message_queue = queue.Queue()  # 消息队列，用于在线程间传递状态信息
        
        # 设置自身进程优先级
        self._set_self_priority()
    
    def _set_self_priority(self):
        """设置自身进程优先级为低于正常"""
        try:
            handle = OpenProcess(PROCESS_ALL_ACCESS, False, os.getpid())
            SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)
            logger.debug("已设置程序优先级为低于正常")
        except Exception as e:
            logger.error(f"设置自身进程优先级失败: {str(e)}")
    
    @property
    def show_notifications(self):
        """获取通知状态"""
        return self.config_manager.show_notifications
    
    @property
    def auto_start(self):
        """获取自启动状态"""
        return self.config_manager.auto_start
    
    @property
    def game_configs(self):
        """获取游戏配置列表"""
        return self.config_manager.game_configs
    
    def refresh_process_cache(self, force=False):
        """
        刷新进程缓存，确保缓存中的进程信息是最新的
        
        Args:
            force (bool): 是否强制刷新缓存
        """
        current_time = time.time()
        if force or (current_time - self.last_cache_refresh) >= self.cache_timeout:
            self.process_cache.clear()
            try:
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name']:
                        self.process_cache[proc.info['name'].lower()] = proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
            self.last_cache_refresh = current_time
    
    def is_process_running(self, process_name):
        """
        检查进程是否在运行
        
        Args:
            process_name (str): 进程名称
            
        Returns:
            psutil.Process or None: 进程对象，未找到则返回None
        """
        if not process_name:
            return None
            
        process_name_lower = process_name.lower()
        
        # 先从缓存中查找
        if process_name_lower in self.process_cache:
            proc = self.process_cache[process_name_lower]
            try:
                if proc.is_running():
                    return proc
                else:
                    del self.process_cache[process_name_lower]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                del self.process_cache[process_name_lower]
        
        # 缓存中没有找到，则遍历所有进程
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == process_name_lower:
                        self.process_cache[process_name_lower] = proc
                        return proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        
        return None
    
    def kill_process(self, process_name):
        """
        终止进程
        
        Args:
            process_name (str): 进程名称
            
        Returns:
            bool: 是否成功终止进程
        """
        proc = self.is_process_running(process_name)
        if proc:
            try:
                proc.kill()
                logger.debug(f"已终止进程: {process_name}")
                if process_name.lower() in self.process_cache:
                    del self.process_cache[process_name.lower()]
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.warning(f"终止进程失败: {process_name} - {str(e)}")
        return False
    
    def set_process_priority_and_affinity(self, process_name):
        """
        设置进程优先级和CPU相关性
        
        Args:
            process_name (str): 进程名称
            
        Returns:
            bool: 是否成功设置
        """
        proc = self.is_process_running(process_name)
        if proc:
            try:
                handle = OpenProcess(PROCESS_ALL_ACCESS, False, proc.pid)
                SetPriorityClass(handle, IDLE_PRIORITY_CLASS)
                
                # 设置CPU亲和性
                cores = psutil.cpu_count(logical=True)
                if cores > 0:
                    small_core = cores - 1
                    proc.cpu_affinity([small_core])
                
                # 设置为效能模式
                self._set_process_eco_qos(proc.pid)
                
                logger.debug(f"优化进程: {process_name}，已设置为效能模式")
                return True
            except Exception as e:
                logger.error(f"优化进程失败: {str(e)}")
        return False
    
    def _set_process_eco_qos(self, pid):
        """
        设置进程为效能模式 (EcoQoS)
        
        Args:
            pid (int): 进程ID
            
        Returns:
            bool: 是否成功设置
        """
        try:
            # 获取SetProcessInformation函数
            SetProcessInformation = ctypes.windll.kernel32.SetProcessInformation
            
            # 打开进程
            process_handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_ALL_ACCESS, False, pid
            )
            
            if not process_handle:
                logger.error(f"无法打开进程(PID: {pid})句柄")
                return False
            
            # 创建并初始化PROCESS_POWER_THROTTLING_STATE结构体
            throttling_state = PROCESS_POWER_THROTTLING_STATE()
            throttling_state.Version = 1
            throttling_state.ControlMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
            throttling_state.StateMask = PROCESS_POWER_THROTTLING_EXECUTION_SPEED
            
            # 调用SetProcessInformation设置效能模式
            result = SetProcessInformation(
                process_handle,
                PROCESS_POWER_THROTTLING_INFORMATION,
                ctypes.byref(throttling_state),
                ctypes.sizeof(throttling_state)
            )
            
            # 关闭进程句柄
            ctypes.windll.kernel32.CloseHandle(process_handle)
            
            if result:
                logger.debug(f"成功将进程(PID: {pid})设置为效能模式")
                return True
            else:
                error = ctypes.windll.kernel32.GetLastError()
                logger.error(f"设置进程效能模式失败，错误码: {error}")
                return False
        except Exception as e:
            logger.error(f"设置进程效能模式时发生异常: {str(e)}")
            return False
    
    def add_message(self, message):
        """
        添加消息到队列
        
        Args:
            message (str): 消息内容
        """
        if self.show_notifications:
            self.message_queue.put(message)
    
    def wait_and_kill_process(self, process_name, max_wait_time=60):
        """
        等待并终止进程，针对ACE进程
        
        Args:
            process_name (str): 进程名称
            max_wait_time (int): 最大等待时间（秒）
            
        Returns:
            bool: 是否成功终止进程
        """
        start_time = time.time()
        while self.running and time.time() - start_time < max_wait_time:
            if self.is_process_running(process_name):
                if self.kill_process(process_name):
                    self.anticheat_killed = True
                    return True
            self.refresh_process_cache(force=True)
            time.sleep(1)
        return False
    
    def wait_and_optimize_process(self, process_name, max_wait_time=60):
        """
        等待并优化进程，针对SGuard64进程
        
        Args:
            process_name (str): 进程名称
            max_wait_time (int): 最大等待时间（秒）
            
        Returns:
            bool: 是否成功优化进程
        """
        start_time = time.time()
        while self.running and time.time() - start_time < max_wait_time:
            if self.is_process_running(process_name):
                if self.set_process_priority_and_affinity(process_name):
                    self.scanprocess_optimized = True
                    return True
            self.refresh_process_cache(force=True)
            time.sleep(1)
        return False
    
    def start_monitor_thread(self, game_config):
        """
        启动游戏监控线程
        
        Args:
            game_config (GameConfig): 游戏配置对象
        """
        if not game_config.monitor_thread or not game_config.monitor_thread.is_alive():
            # 先添加通知消息
            self.add_message(f"已启动 {game_config.name} 监控")
            logger.debug(f"已启动 {game_config.name} 监控线程")
            
            # 检查游戏是否已经在运行
            main_proc = self.is_process_running(game_config.main_game)
            if main_proc:
                game_config.main_game_running = True
                self.main_game_running = True
                logger.debug(f"{game_config.name} 主进程已经在运行，立即检查反作弊和扫描进程")
                
                # 强制刷新进程缓存
                self.refresh_process_cache(force=True)
                
                # 检查反作弊进程状态
                anticheat_proc = self.is_process_running(self.anticheat_name)
                if anticheat_proc and not game_config.anticheat_handled:
                    logger.debug(f"检测到 {self.anticheat_name} 正在运行，尝试终止")
                    if self.kill_process(self.anticheat_name):
                        game_config.anticheat_handled = True
                        self.anticheat_killed = True  # 更新全局状态
                        logger.debug(f"已终止 {self.anticheat_name}")
                elif not anticheat_proc:
                    # 如果进程不存在，也认为是已处理的
                    game_config.anticheat_handled = True
                    self.anticheat_killed = True  # 更新全局状态
                    logger.debug(f"{self.anticheat_name} 进程不存在，标记为已处理")
                
                # 检查扫描进程状态
                scan_proc = self.is_process_running(self.scanprocess_name)
                if scan_proc and not game_config.scanprocess_handled:
                    logger.debug(f"检测到 {self.scanprocess_name} 正在运行，尝试优化")
                    if self.set_process_priority_and_affinity(self.scanprocess_name):
                        game_config.scanprocess_handled = True
                        self.scanprocess_optimized = True  # 更新全局状态
                        logger.debug(f"已优化 {self.scanprocess_name}")
                    elif not scan_proc:
                        # 如果进程不存在，也记录为已处理过
                        game_config.scanprocess_handled = True
                        self.scanprocess_optimized = True  # 更新全局状态
                        logger.debug(f"{self.scanprocess_name} 进程不存在，标记为已处理")
            
            # 然后再启动监控线程
            game_config.monitor_thread = threading.Thread(
                target=self.monitor_game_process,
                args=(game_config,)
            )
            game_config.monitor_thread.daemon = True
            game_config.monitor_thread.start()
    
    def stop_monitor_thread(self, game_config):
        """
        停止游戏监控线程
        
        Args:
            game_config (GameConfig): 游戏配置对象
        """
        if game_config.monitor_thread and game_config.monitor_thread.is_alive():
            game_config.main_game_running = False
            self.main_game_running = False  # 同步更新主监视器的状态
            game_config.anticheat_handled = False
            game_config.scanprocess_handled = False
            logger.debug(f"已停止 {game_config.name} 监控线程")
            self.add_message(f"已停止 {game_config.name} 监控")
    
    def check_process_status(self, process_name):
        """
        检查进程状态，判断是否已被处理
        
        Args:
            process_name (str): 进程名称
            
        Returns:
            tuple: (是否运行, 是否已优化)
        """
        proc = self.is_process_running(process_name)
        if not proc:
            return False, False
            
        # 进程存在，检查是否已优化
        is_optimized = False
        
        if process_name.lower() == self.scanprocess_name.lower():
            try:
                # 检查CPU亲和性（这个不涉及Windows API调用，较为安全）
                try:
                    cpu_affinity = proc.cpu_affinity()
                    cores = psutil.cpu_count(logical=True)
                    expected_core = [cores - 1] if cores > 0 else None
                    
                    # 判断CPU亲和性是否符合优化要求
                    affinity_optimized = (expected_core is not None and cpu_affinity == expected_core)
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.debug(f"检查CPU亲和性失败: {str(e)}")
                    affinity_optimized = False
                
                # 检查进程优先级
                # 使用psutil的nice/ionice方法代替直接Windows API调用
                try:
                    # 在Windows上，nice()返回的是进程优先级类
                    priority = proc.nice()
                    priority_optimized = (priority == IDLE_PRIORITY_CLASS)
                    
                    logger.debug(f"{process_name} 状态检查: 优先级={priority}, CPU亲和性={cpu_affinity if 'cpu_affinity' in locals() else 'unknown'}")
                    
                    # 判断是否已优化：优先级为IDLE_PRIORITY_CLASS且CPU亲和性已设置为最后一个核心
                    is_optimized = priority_optimized and affinity_optimized
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.debug(f"检查进程优先级失败: {str(e)}")
                
            except Exception as e:
                logger.error(f"检查进程状态失败: {str(e)}")
                
        return True, is_optimized
    
    def monitor_game_process(self, game_config):
        """
        监控特定游戏进程
        
        Args:
            game_config (GameConfig): 游戏配置对象
        """
        # 检测计数器
        check_counter = 0
        # 游戏启动器进程是否运行中标记
        launcher_running = False
        
        # 循环监控游戏主进程和启动器进程
        while self.running and game_config.enabled:
            # 每10次循环刷新一次进程缓存，减少系统资源消耗
            if check_counter % 10 == 0:
                self.refresh_process_cache()
            check_counter += 1
            
            # 检测游戏主进程
            main_proc = self.is_process_running(game_config.main_game)
            
            # 游戏主进程状态变化：未运行->运行
            if main_proc and not game_config.main_game_running:
                game_config.main_game_running = True
                self.main_game_running = True  # 同步更新主监视器的状态
                self.add_message(f"检测到 {game_config.name} 主进程启动")
                logger.debug(f"检测到 {game_config.name} 主进程启动")
                
                # 只在检测到游戏进程时强制刷新缓存，避免频繁刷新
                self.refresh_process_cache(force=True)
                
                # 处理反作弊进程和扫描进程
                if not game_config.anticheat_handled and self.anticheat_name:
                    if self.wait_and_kill_process(self.anticheat_name):
                        game_config.anticheat_handled = True
                        self.anticheat_killed = True  # 更新全局状态
                
                if not game_config.scanprocess_handled and self.scanprocess_name:
                    if self.wait_and_optimize_process(self.scanprocess_name):
                        game_config.scanprocess_handled = True
                        self.scanprocess_optimized = True  # 更新全局状态
            
            # 游戏主进程运行中，检查反作弊和扫描进程状态
            elif main_proc and game_config.main_game_running:
                # 定期检查反作弊进程，可能会被游戏重新启动
                if not game_config.anticheat_handled and self.anticheat_name:
                    anticheat_running, _ = self.check_process_status(self.anticheat_name)
                    if anticheat_running:
                        logger.debug(f"游戏运行中检测到 {self.anticheat_name}，尝试终止")
                        if self.kill_process(self.anticheat_name):
                            game_config.anticheat_handled = True
                            self.anticheat_killed = True  # 更新全局状态
                
                # 定期检查扫描进程状态，可能会被重置或重新启动
                if not game_config.scanprocess_handled and self.scanprocess_name:
                    scan_running, is_optimized = self.check_process_status(self.scanprocess_name)
                    if scan_running and not is_optimized:
                        logger.debug(f"游戏运行中检测到未优化的 {self.scanprocess_name}，尝试优化")
                        if self.set_process_priority_and_affinity(self.scanprocess_name):
                            game_config.scanprocess_handled = True
                            self.scanprocess_optimized = True  # 更新全局状态
                
                # 更新全局状态标志，保持与任何活动游戏配置的状态一致
                self._update_global_status_flags()
            
            # 游戏主进程状态变化：运行->未运行
            elif not main_proc and game_config.main_game_running:
                game_config.main_game_running = False
                game_config.anticheat_handled = False
                game_config.scanprocess_handled = False
                
                # 更新主监视器的状态
                self.main_game_running = self._any_game_running()
                
                # 如果没有任何游戏在运行，重置进程状态标志
                if not self.main_game_running:
                    self.anticheat_killed = False
                    self.scanprocess_optimized = False
                
                self.add_message(f"{game_config.name} 主进程已关闭")
                logger.debug(f"{game_config.name} 主进程已关闭")
            
            # 检测启动器进程
            launcher_proc = self.is_process_running(game_config.launcher)
            
            # 启动器状态变化：未运行->运行
            if launcher_proc and not launcher_running:
                launcher_running = True
                self.add_message(f"检测到 {game_config.name} 启动器正在运行")
                logger.debug(f"检测到 {game_config.name} 启动器正在运行，PID: {launcher_proc.pid}")
            
            # 启动器状态变化：运行->未运行
            elif not launcher_proc and launcher_running:
                launcher_running = False
                self.add_message(f"{game_config.name} 启动器已关闭")
                logger.debug(f"{game_config.name} 启动器已关闭")
            
            # 降低检测频率，减少CPU使用率
            time.sleep(3)
    
    def _any_game_running(self):
        """
        检查是否有任何游戏在运行
        
        Returns:
            bool: 是否有游戏在运行
        """
        return any(game.main_game_running for game in self.game_configs if game.enabled)
    
    def _update_global_status_flags(self):
        """
        更新全局状态标志，保持与游戏配置的状态一致
        """
        # 如果有任何一个游戏已处理了反作弊进程，全局状态设为已处理
        if any(game.anticheat_handled for game in self.game_configs if game.enabled and game.main_game_running):
            self.anticheat_killed = True
        
        # 如果有任何一个游戏已处理了扫描进程，全局状态设为已处理
        if any(game.scanprocess_handled for game in self.game_configs if game.enabled and game.main_game_running):
            self.scanprocess_optimized = True
    
    def get_game_config_by_name(self, game_name):
        """
        根据游戏名称获取游戏配置
        
        Args:
            game_name (str): 游戏名称
            
        Returns:
            GameConfig or None: 游戏配置对象，未找到则返回None
        """
        return self.config_manager.get_game_config(game_name)
    
    def start_all_enabled_monitors(self):
        """启动所有已启用的游戏监控线程"""
        enabled_games = [game for game in self.game_configs if game.enabled]
        
        if not enabled_games:
            logger.debug("未启用任何游戏监控，不启动监控线程")
            self.running = False
            return
        
        # 有启用的游戏，设置running为True
        self.running = True
        logger.debug("监控程序已启动")
            
        for game_config in enabled_games:
            self.start_monitor_thread(game_config)
    
    def stop_all_monitors(self):
        """停止所有游戏监控线程"""
        for game_config in self.game_configs:
            self.stop_monitor_thread(game_config)
        
        # 设置运行标志为False
        self.running = False
        logger.debug("监控程序已停止") 