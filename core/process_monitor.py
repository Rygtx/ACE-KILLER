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
        self.running = True  # 监控线程运行标记
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
            logger.info("已设置程序优先级为低于正常")
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
                logger.info(f"已终止进程: {process_name}")
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
                
                cores = psutil.cpu_count(logical=True)
                if cores > 0:
                    small_core = cores - 1
                    proc.cpu_affinity([small_core])
                    logger.info(f"优化进程: {process_name}")
                    return True
            except Exception as e:
                logger.error(f"优化进程失败: {str(e)}")
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
            logger.info(f"已启动 {game_config.name} 监控线程")
            
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
            logger.info(f"已停止 {game_config.name} 监控线程")
            self.add_message(f"已停止 {game_config.name} 监控")
    
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
                logger.info(f"检测到 {game_config.name} 主进程启动")
                
                # 只在检测到游戏进程时强制刷新缓存，避免频繁刷新
                self.refresh_process_cache(force=True)
                
                # 处理反作弊进程和扫描进程
                if not game_config.anticheat_handled and self.anticheat_name:
                    game_config.anticheat_handled = self.wait_and_kill_process(self.anticheat_name)
                
                if not game_config.scanprocess_handled and self.scanprocess_name:
                    game_config.scanprocess_handled = self.wait_and_optimize_process(self.scanprocess_name)
            
            # 游戏主进程状态变化：运行->未运行
            elif not main_proc and game_config.main_game_running:
                game_config.main_game_running = False
                self.main_game_running = False  # 同步更新主监视器的状态
                game_config.anticheat_handled = False
                game_config.scanprocess_handled = False
                self.add_message(f"{game_config.name} 主进程已关闭")
                logger.info(f"{game_config.name} 主进程已关闭")
            
            # 检测启动器进程
            launcher_proc = self.is_process_running(game_config.launcher)
            
            # 启动器状态变化：未运行->运行
            if launcher_proc and not launcher_running:
                launcher_running = True
                self.add_message(f"检测到 {game_config.name} 启动器正在运行")
                logger.info(f"检测到 {game_config.name} 启动器正在运行，PID: {launcher_proc.pid}")
            
            # 启动器状态变化：运行->未运行
            elif not launcher_proc and launcher_running:
                launcher_running = False
                self.add_message(f"{game_config.name} 启动器已关闭")
                logger.info(f"{game_config.name} 启动器已关闭")
            
            # 降低检测频率，减少CPU使用率
            time.sleep(3)
    
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
        for game_config in self.game_configs:
            if game_config.enabled:
                self.start_monitor_thread(game_config)
    
    def stop_all_monitors(self):
        """停止所有游戏监控线程"""
        for game_config in self.game_configs:
            self.stop_monitor_thread(game_config)
        
        # 设置运行标志为False
        self.running = False 