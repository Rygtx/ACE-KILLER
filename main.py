#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes
import datetime
import os
import queue
import subprocess
import sys
import threading
import time
import winreg

import psutil
import yaml
from PIL import Image
from loguru import logger
from pystray import MenuItem, Menu, Icon
from win32api import OpenProcess
from win32con import PROCESS_ALL_ACCESS
from win32process import SetPriorityClass, IDLE_PRIORITY_CLASS, BELOW_NORMAL_PRIORITY_CLASS
from win11toast import notify


class GameConfig:
    def __init__(self, name: str, launcher: str, main_game: str, enabled: bool):
        self.name = name
        self.launcher = launcher
        self.main_game = main_game
        self.enabled = bool(enabled)
        self.monitor_thread = None
        self.main_game_running = False
        self.anticheat_handled = False
        self.scanprocess_handled = False
        self.game_dir = ""  # 游戏目录


class GameProcessMonitor:
    def __init__(self):
        self.anticheat_name = "ACE-Tray.exe"
        self.scanprocess_name = "SGuard64.exe"
        self.running = True  # 监控线程运行标记
        self.main_game_running = False  # 游戏主进程是否运行中标记
        self.process_cache = {}
        self.cache_timeout = 5
        self.last_cache_refresh = 0
        self.anticheat_killed = False  # 终止ACE进程标记
        self.scanprocess_optimized = False  # 优化SGuard64进程标记
        self.config_dir = os.path.join(os.path.expanduser("~"), ".ace-killer")  # 配置目录名称更新为ace-killer
        self.log_dir = os.path.join(self.config_dir, "logs")  # 日志目录
        self.config_file = os.path.join(self.config_dir, "config.yaml")  # 配置文件路径
        self.show_notifications = True  # Windows通知开关默认值
        self.auto_start = False  # 开机自启动开关默认值
        self.message_queue = queue.Queue()  # 消息队列，用于在线程间传递状态信息
        self.game_configs = []  # 游戏配置列表

        # 日志相关默认设置
        self.log_retention_days = 7  # 默认日志保留天数
        self.log_rotation = "1 day"  # 默认日志轮转周期

        # 确保配置目录存在
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
                logger.info(f"已创建配置目录: {self.config_dir}")
            except Exception as e:
                logger.error(f"创建配置目录失败: {str(e)}")

        # 确保日志目录存在
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
                logger.info(f"已创建日志目录: {self.log_dir}")
            except Exception as e:
                logger.error(f"创建日志目录失败: {str(e)}")

        # 先配置日志系统
        self.setup_logger()

        # 然后加载或创建配置文件
        self.load_config()

        # 设置自身进程优先级
        try:
            handle = OpenProcess(PROCESS_ALL_ACCESS, False, os.getpid())
            SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)
        except Exception as e:
            logger.error(f"设置自身进程优先级失败: {str(e)}")

    # 加载配置文件
    def load_config(self):
        default_config = {
            'notifications': {
                'enabled': True
            },
            'logging': {
                'retention_days': 7,
                'rotation': '1 day'
            },
            'application': {
                'auto_start': False
            },
            'games': [
                {
                    'name': '无畏契约',
                    'launcher': '无畏契约登录器.exe',
                    'main_game': 'VALORANT-Win64-Shipping.exe',
                    'game_dir': '',
                    'enabled': True
                },
                {
                    "name": "三角洲行动",
                    "launcher": "delta_force_launcher.exe",
                    "main_game": "DeltaForceClient-Win64-Shipping.exe",
                    'game_dir': '',
                    "enabled": False,
                }
            ]
        }

        # 如果配置文件存在，则读取
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)

                # 如果配置文件为空或无效，使用默认配置
                if not config_data:
                    config_data = default_config
                    logger.warning("配置文件为空或无效，将使用默认配置")

                # 读取通知设置
                if 'notifications' in config_data and 'enabled' in config_data['notifications']:
                    self.show_notifications = bool(config_data['notifications']['enabled'])
                    logger.info(f"已从配置文件加载通知设置: {self.show_notifications}")

                # 读取日志设置
                if 'logging' in config_data:
                    if 'retention_days' in config_data['logging']:
                        self.log_retention_days = int(config_data['logging']['retention_days'])
                    if 'rotation' in config_data['logging']:
                        self.log_rotation = config_data['logging']['rotation']

                # 读取开机自启设置
                if 'application' in config_data and 'auto_start' in config_data['application']:
                    self.auto_start = bool(config_data['application']['auto_start'])
                    # 检查实际注册表状态与配置是否一致
                    actual_auto_start = self.check_auto_start()
                    if self.auto_start != actual_auto_start:
                        logger.warning(
                            f"开机自启配置与实际状态不一致，配置为:{self.auto_start}，实际为:{actual_auto_start}，将以配置为准")

                    # 确保注册表状态与配置一致
                    if self.auto_start:
                        self.enable_auto_start()
                    else:
                        self.disable_auto_start()

                    logger.info(f"已从配置文件加载开机自启设置: {self.auto_start}")
                else:
                    # 如果配置中没有自启设置，检查注册表中是否已设置
                    if self.check_auto_start():
                        # 如果注册表中已设置，则更新配置
                        self.auto_start = True
                        logger.info("检测到注册表中已设置开机自启，已更新配置")

                # 加载游戏配置
                if 'games' in config_data and isinstance(config_data['games'], list):
                    for game_data in config_data['games']:
                        if all(k in game_data for k in ['name', 'launcher', 'main_game', 'enabled']):
                            game_config = GameConfig(
                                name=game_data['name'],
                                launcher=game_data['launcher'],
                                main_game=game_data['main_game'],
                                enabled=game_data['enabled']
                            )
                            if 'game_dir' in game_data:
                                game_config.game_dir = game_data['game_dir']
                            self.game_configs.append(game_config)

                    logger.info(f"已从配置文件加载 {len(self.game_configs)} 个游戏配置")

                logger.info("配置文件加载成功")
            except Exception as e:
                logger.error(f"加载配置文件失败: {str(e)}")
                # 使用默认配置
                self._create_default_config(default_config)
        else:
            # 如果配置文件不存在，则创建默认配置文件
            logger.info("配置文件不存在，将创建默认配置文件")
            self._create_default_config(default_config)

    # 创建默认配置文件
    def _create_default_config(self, default_config):
        try:
            # 使用默认配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)

            # 从默认配置中加载设置
            self.show_notifications = default_config['notifications']['enabled']
            self.log_retention_days = default_config['logging']['retention_days']
            self.log_rotation = default_config['logging']['rotation']
            self.auto_start = default_config['application']['auto_start']

            # 加载默认游戏配置
            for game_data in default_config['games']:
                game_config = GameConfig(
                    name=game_data['name'],
                    launcher=game_data['launcher'],
                    main_game=game_data['main_game'],
                    enabled=game_data['enabled']
                )
                self.game_configs.append(game_config)

            logger.info("已创建并加载默认配置")
        except Exception as e:
            logger.error(f"创建默认配置文件失败: {str(e)}")

    # 保存配置文件
    def save_config(self):
        try:
            # 构建配置数据
            config_data = {
                'notifications': {
                    'enabled': self.show_notifications
                },
                'logging': {
                    'retention_days': self.log_retention_days,
                    'rotation': self.log_rotation
                },
                'application': {
                    'auto_start': self.auto_start
                },
                'games': []
            }

            # 添加游戏配置
            for game_config in self.game_configs:
                game_data = {
                    'name': game_config.name,
                    'launcher': game_config.launcher,
                    'main_game': game_config.main_game,
                    'enabled': game_config.enabled,
                    'game_dir': game_config.game_dir
                }
                config_data['games'].append(game_data)

            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

            logger.info("配置已保存")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False

    # 配置日志系统
    def setup_logger(self):
        # 移除默认的日志处理器
        logger.remove()

        # 获取当前日期作为日志文件名的一部分
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f"{today}.log")

        # 添加文件日志处理器，配置轮转和保留策略，写入到文件中
        logger.add(
            log_file,
            rotation=self.log_rotation,  # 日志轮转周期
            retention=f"{self.log_retention_days} days",  # 日志保留天数
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
            level="INFO",
            encoding="utf-8"
        )

        # 判断是否为打包的可执行文件，以及是否有控制台
        is_frozen = getattr(sys, 'frozen', False)
        has_console = True

        # 在Windows下，检查是否有控制台窗口
        if is_frozen and sys.platform == 'win32':
            try:
                # 检查标准错误输出是否存在
                if sys.stderr is None or not sys.stderr.isatty():
                    has_console = False
            except (AttributeError, IOError):
                has_console = False

        # 只有在有控制台的情况下才添加控制台日志处理器
        if has_console:
            # 添加控制台日志处理器，输出到控制台
            logger.add(
                sys.stderr,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
                level="INFO",
                colorize=True
            )
            logger.info("已添加控制台日志处理器")
        else:
            logger.info("检测到无控制台环境，不添加控制台日志处理器")

        logger.info(f"日志系统已初始化，日志文件: {log_file}")
        logger.info(f"日志保留天数: {self.log_retention_days}，轮转周期: {self.log_rotation}")

    # 刷新进程缓存，确保缓存中的进程信息是最新的
    def refresh_process_cache(self, force=False):
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

    # 检查进程是否在运行
    def is_process_running(self, process_name):
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

    # 终止进程
    def kill_process(self, process_name):
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

    # 设置进程优先级和CPU相关性
    def set_process_priority_and_affinity(self, process_name):
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

    # 添加消息到队列
    def add_message(self, message):
        if self.show_notifications:
            self.message_queue.put(message)

    # 等待并终止进程，针对ACE进程
    def wait_and_kill_process(self, process_name, max_wait_time=60):
        start_time = time.time()
        while self.running and time.time() - start_time < max_wait_time:
            if self.is_process_running(process_name):
                if self.kill_process(process_name):
                    self.anticheat_killed = True
                    return True
            self.refresh_process_cache(force=True)
            time.sleep(1)
        return False

    # 等待并优化进程，针对SGuard64进程
    def wait_and_optimize_process(self, process_name, max_wait_time=60):
        start_time = time.time()
        while self.running and time.time() - start_time < max_wait_time:
            if self.is_process_running(process_name):
                if self.set_process_priority_and_affinity(process_name):
                    self.scanprocess_optimized = True
                    return True
            self.refresh_process_cache(force=True)
            time.sleep(1)
        return False

    # 启动游戏监控线程
    def start_monitor_thread(self, game_config):
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

    # 停止游戏监控线程
    def stop_monitor_thread(self, game_config):
        if game_config.monitor_thread and game_config.monitor_thread.is_alive():
            game_config.main_game_running = False
            self.main_game_running = False  # 同步更新主监视器的状态
            game_config.anticheat_handled = False
            game_config.scanprocess_handled = False
            logger.info(f"已停止 {game_config.name} 监控线程")
            self.add_message(f"已停止 {game_config.name} 监控")

    # 监控特定游戏进程
    def monitor_game_process(self, game_config):
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

                # 如果游戏目录未设置，尝试从主进程获取
                if not game_config.game_dir:
                    self.get_game_directory(game_config)

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
                
                # 尝试获取游戏目录
                if not game_config.game_dir:
                    self.get_game_directory(game_config, launcher_proc)

            # 启动器状态变化：运行->未运行
            elif not launcher_proc and launcher_running:
                launcher_running = False
                self.add_message(f"{game_config.name} 启动器已关闭")
                logger.info(f"{game_config.name} 启动器已关闭")

            # 降低检测频率，减少CPU使用率
            time.sleep(3)

    # 获取游戏目录
    def get_game_directory(self, game_config, launcher_proc=None):
        try:
            # 如果游戏目录已经找到，直接返回
            if game_config.game_dir and os.path.exists(game_config.game_dir):
                logger.info(f"{game_config.name} 游戏目录已存在: {game_config.game_dir}")
                return True
                
            # 首先尝试从主游戏进程获取目录
            main_game_proc = self.is_process_running(game_config.main_game)
            if main_game_proc:
                try:
                    main_game_path = main_game_proc.exe()
                    if main_game_path and os.path.exists(main_game_path):
                        main_game_dir = os.path.dirname(main_game_path)
                        game_config.game_dir = main_game_dir
                        logger.info(f"从运行中的游戏主进程获取到 {game_config.name} 游戏目录: {main_game_dir}")
                        self.save_config()
                        return True
                except Exception as e:
                    logger.error(f"获取游戏主进程路径时出错: {str(e)}")
            
            # 如果没有提供启动器进程，尝试找到它
            if launcher_proc is None:
                launcher_proc = self.is_process_running(game_config.launcher)
            
            # 如果找到了启动器进程，尝试通过它找到游戏目录
            if launcher_proc:
                try:
                    # 获取启动器进程的可执行文件路径
                    launcher_path = launcher_proc.exe()
                    if launcher_path and os.path.exists(launcher_path):
                        launcher_dir = os.path.dirname(launcher_path)
                        logger.info(f"找到 {game_config.name} 启动器目录: {launcher_dir}")
                        
                        # 尝试查找游戏主进程目录
                        main_game_path = self.find_main_game_path(launcher_dir, game_config.main_game)
                        if main_game_path:
                            main_game_dir = os.path.dirname(main_game_path)
                            game_config.game_dir = main_game_dir
                            logger.info(f"从启动器目录找到 {game_config.name} 游戏目录: {main_game_dir}")
                            # 保存配置到文件
                            self.save_config()
                            return True
                except Exception as e:
                    logger.error(f"通过启动器获取游戏目录时出错: {str(e)}")
            
            # 如果都没找到，发送通知提示用户先开启游戏
            self.add_message(f"未找到 {game_config.name} 游戏目录，请先开启一次游戏主程序")
            logger.warning(f"未找到 {game_config.name} 游戏目录，建议用户先启动游戏")
            return False
                
        except Exception as e:
            logger.error(f"获取游戏目录时出错: {str(e)}")
            return False

    # 递归查找游戏主进程可执行文件
    def find_main_game_path(self, start_dir, main_game_name, max_depth=3):
        try:
            # 在当前目录搜索
            for item in os.listdir(start_dir):
                item_path = os.path.join(start_dir, item)
                
                # 检查是否是文件并且名称匹配
                if os.path.isfile(item_path) and item.lower() == main_game_name.lower():
                    return item_path
                
                # 如果是目录且未超过最大深度，递归搜索
                if os.path.isdir(item_path) and max_depth > 0:
                    found_path = self.find_main_game_path(item_path, main_game_name, max_depth - 1)
                    if found_path:
                        return found_path
            
            # 如果在启动器目录没有找到，检查上一级目录
            parent_dir = os.path.dirname(start_dir)
            if parent_dir and parent_dir != start_dir:  # 防止无限循环
                for item in os.listdir(parent_dir):
                    item_path = os.path.join(parent_dir, item)
                    
                    # 检查是否是文件并且名称匹配
                    if os.path.isfile(item_path) and item.lower() == main_game_name.lower():
                        return item_path
            
            return None
        except Exception as e:
            logger.error(f"查找游戏主进程路径时出错: {str(e)}")
            return None

    # 根据游戏名称获取游戏配置
    def get_game_config_by_name(self, game_name):
        for game_config in self.game_configs:
            if game_config.name == game_name:
                return game_config
        return None

    # 根据游戏名称获取游戏目录
    def get_game_directory_by_name(self, game_name):
        game_config = self.get_game_config_by_name(game_name)
        if game_config:
            return game_config.game_dir
        return None

    # 尝试获取所有游戏目录
    def get_all_game_directories(self):
        success_count = 0
        for game_config in self.game_configs:
            # 检查是否已经有游戏目录
            if not game_config.game_dir:
                # 尝试找到启动器进程
                launcher_proc = self.is_process_running(game_config.launcher)
                if launcher_proc:
                    if self.get_game_directory(game_config, launcher_proc):
                        success_count += 1
                else:
                    logger.info(f"{game_config.name} 启动器未运行，无法获取游戏目录")
            else:
                logger.info(f"{game_config.name} 游戏目录已设置: {game_config.game_dir}")
                success_count += 1
        
        if success_count == len(self.game_configs):
            self.add_message("已成功获取所有游戏目录")
            return True
        elif success_count > 0:
            self.add_message(f"已获取 {success_count}/{len(self.game_configs)} 个游戏目录")
            return True
        else:
            self.add_message("未能获取任何游戏目录，请确保游戏启动器正在运行")
            return False

    # 获取程序完整路径
    def get_program_path(self):
        if getattr(sys, 'frozen', False):
            return sys.executable
        else:
            # 直接运行的python脚本
            return os.path.abspath(sys.argv[0])

    # 检查是否设置了开机自启
    def check_auto_start(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0,
                                 winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, "ACE-KILLER")
                winreg.CloseKey(key)
                # 检查注册表中的路径是否与当前程序路径一致
                expected_path = f'"{self.get_program_path()}"'
                if value.lower() != expected_path.lower():
                    logger.warning(f"注册表中的自启路径与当前程序路径不一致，将更新。注册表:{value}，当前:{expected_path}")
                    # 更新为正确的路径
                    self.enable_auto_start()
                return True
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            logger.error(f"检查开机自启状态失败: {str(e)}")
            return False

    # 设置开机自启
    def enable_auto_start(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0,
                                 winreg.KEY_SET_VALUE)
            program_path = self.get_program_path()
            winreg.SetValueEx(key, "ACE-KILLER", 0, winreg.REG_SZ, f'"{program_path}"')
            winreg.CloseKey(key)
            logger.info("已设置开机自启")
            return True
        except Exception as e:
            logger.error(f"设置开机自启失败: {str(e)}")
            return False

    # 取消开机自启
    def disable_auto_start(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0,
                                 winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, "ACE-KILLER")
            except FileNotFoundError:
                # 注册表项不存在，无需删除
                pass
            winreg.CloseKey(key)
            logger.info("已取消开机自启")
            return True
        except Exception as e:
            logger.error(f"取消开机自启失败: {str(e)}")
            return False


# 判断是否以管理员权限运行
def run_as_admin():
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return False
    return True


# 获取程序状态信息
def get_status_info(monitor):
    if not monitor:
        return "程序未启动"

    status_lines = []
    status_lines.append("🟢 监控程序运行中" if monitor.running else "🔴 监控程序已停止")

    # 检查是否有任何游戏在运行
    running_games = [game_config.name for game_config in monitor.game_configs 
                     if game_config.enabled and game_config.main_game_running]
    any_game_running = bool(running_games)
    
    # 如果至少有一个游戏在运行，也更新monitor的状态
    if any_game_running and not monitor.main_game_running:
        monitor.main_game_running = True
    # 如果没有游戏在运行但monitor状态显示有游戏在运行，更新monitor状态
    elif not any_game_running and monitor.main_game_running:
        monitor.main_game_running = False
        
    if any_game_running:
        status_lines.append(f"🎮 游戏主程序：运行中 ({', '.join(running_games)})")
        status_lines.append("✅ ACE进程：已终止" if monitor.anticheat_killed else "❓ ACE进程：未处理")
        status_lines.append("✅ SGuard64进程：已优化" if monitor.scanprocess_optimized else "❓ SGuard64进程：未处理")
    else:
        status_lines.append("🎮 游戏主程序：未运行")

    # 添加各个游戏的目录信息
    status_lines.append("📂 游戏目录信息：")
    game_dir_found = False
    for game_config in monitor.game_configs:
        if game_config.game_dir:
            status_lines.append(f"  ✓ {game_config.name}：{game_config.game_dir}")
            game_dir_found = True
        else:
            status_lines.append(f"  ✗ {game_config.name}：未找到目录")
    
    if not game_dir_found:
        status_lines.append("  提示：请启动游戏或点击「刷新游戏目录」")

    status_lines.append("\n⚙️ 系统设置：")
    status_lines.append("  🔔 通知状态：" + ("开启" if monitor.show_notifications else "关闭"))
    status_lines.append(f"  🔁 开机自启：{'开启' if monitor.auto_start else '关闭'}")
    status_lines.append(f"  📁 配置目录：{monitor.config_dir}")
    status_lines.append(f"  📝 日志目录：{monitor.log_dir}")
    status_lines.append(f"  ⏱️ 日志保留：{monitor.log_retention_days}天")

    return "\n".join(status_lines)


# 创建托盘菜单
def create_tray_icon(monitor, icon_path):
    # 载入图标
    image = Image.open(icon_path)

    # 定义菜单项动作函数
    def toggle_notifications():
        monitor.show_notifications = not monitor.show_notifications
        # 保存配置
        if monitor.save_config():
            logger.info(f"通知状态已更改并保存: {'开启' if monitor.show_notifications else '关闭'}")
        else:
            logger.warning(f"通知状态已更改但保存失败: {'开启' if monitor.show_notifications else '关闭'}")

    def is_notifications_enabled(item):
        return monitor.show_notifications

    def toggle_auto_start():
        monitor.auto_start = not monitor.auto_start
        if monitor.auto_start:
            monitor.enable_auto_start()
        else:
            monitor.disable_auto_start()
        # 保存配置
        if monitor.save_config():
            logger.info(f"开机自启状态已更改并保存: {'开启' if monitor.auto_start else '关闭'}")
        else:
            logger.warning(f"开机自启状态已更改但保存失败: {'开启' if monitor.auto_start else '关闭'}")

    def is_auto_start_enabled(item):
        return monitor.auto_start

    def show_status():
        status = get_status_info(monitor)
        icon = {
            'src': icon_path,
            'placement': 'appLogoOverride'  # 方形icon
        }
        notify(
            app_id="ACE-KILLER",
            title="ACE-KILLER 状态",
            body=status,
            icon=icon,
            audio={'silent': 'true'},    # 取消响铃
        )
        
    def refresh_game_directories():
        if monitor.get_all_game_directories():
            notify(
                app_id="ACE-KILLER",
                title="游戏目录刷新",
                body="游戏目录刷新完成",
                icon=icon_path,
                duration="short"
            )
        else:
            notify(
                app_id="ACE-KILLER",
                title="游戏目录刷新",
                body="未能获取任何游戏目录，请确保游戏启动器或主程序正在运行",
                icon=icon_path,
                duration="short"
            )

    # 创建游戏开关菜单项
    game_menu_items = []
    for game in monitor.game_configs:
        def make_toggle_callback(g):
            def callback():
                g.enabled = not g.enabled
                if g.enabled:
                    monitor.start_monitor_thread(g)
                else:
                    monitor.stop_monitor_thread(g)
                monitor.save_config()

            return callback

        game_menu_items.append(
            MenuItem(
                f'{game.name}',
                make_toggle_callback(game),
                checked=lambda _, g=game: g.enabled
            )
        )

    def open_config_dir():
        try:
            # 使用系统默认的文件浏览器打开配置目录
            if os.path.exists(monitor.config_dir):
                subprocess.Popen(f'explorer "{monitor.config_dir}"')
                logger.info(f"已打开配置目录: {monitor.config_dir}")
            else:
                # 如果目录不存在，尝试创建
                os.makedirs(monitor.config_dir, exist_ok=True)
                subprocess.Popen(f'explorer "{monitor.config_dir}"')
                logger.info(f"已创建并打开配置目录: {monitor.config_dir}")
        except Exception as e:
            logger.error(f"打开配置目录失败: {str(e)}")

    def exit_app():
        monitor.running = False
        tray_icon.stop()

    # 创建菜单
    menu = Menu(
        MenuItem('显示状态', show_status),
        MenuItem('切换通知', toggle_notifications, checked=is_notifications_enabled),
        MenuItem('开机自启', toggle_auto_start, checked=is_auto_start_enabled),
        Menu.SEPARATOR,
        MenuItem('游戏监控', Menu(*game_menu_items)),
        Menu.SEPARATOR,
        MenuItem('刷新游戏目录', refresh_game_directories),
        MenuItem('打开配置目录', open_config_dir),
        Menu.SEPARATOR,
        MenuItem('退出', exit_app)
    )

    # 创建托盘图标
    tray_icon = Icon("ace-killer", image, "ACE-KILLER", menu)

    return tray_icon


# 通知处理线程
def notification_thread(monitor, icon_path):
    while monitor.running:
        try:
            # 获取消息，最多等待0.5秒
            message = monitor.message_queue.get(timeout=0.1)
            notify(
                app_id="ACE-KILLER",
                title="ACE-KILLER 消息通知",
                body=message,
                icon=icon_path,
                duration="short"
            )
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"通知发送失败: {str(e)}")


def main():
    if not run_as_admin():
        return

    # 创建监控线程
    monitor = GameProcessMonitor()

    # 现在日志系统已初始化，可以记录启动信息
    logger.info("🟩 ACE-KILLER 程序已启动！")

    # 初始化通知组件 - 查找图标文件
    base_path = os.path.dirname(os.path.abspath(__file__))
    icon_paths = [
        # 标准开发环境路径
        os.path.join(base_path, 'assets', 'icon', 'favicon.ico'),
        # 打包环境路径
        os.path.join(os.path.dirname(sys.executable), 'favicon.ico')
    ]
    
    # 静默查找图标文件，使用第一个存在的路径
    icon_path = next((path for path in icon_paths if os.path.exists(path)), None)
    
    # 创建通知处理线程
    notification_thread_obj = threading.Thread(
        target=notification_thread,
        args=(monitor, icon_path)
    )
    notification_thread_obj.daemon = True
    notification_thread_obj.start()

    # 创建并运行系统托盘图标
    tray_icon = create_tray_icon(monitor, icon_path)

    buttons=[
        {'activationType': 'protocol', 'arguments': 'https://github.com/cassianvale/ACE-KILLER', 'content': '访问项目地址'},
        {'activationType': 'protocol', 'arguments': 'https://github.com/cassianvale/ACE-KILLER/releases/latest', 'content': '获取最新版本'}
    ]
    
    # 显示欢迎通知
    notify(
        app_id="ACE-KILLER",
        body=f"🚀 启动成功！欢迎使用 ACE-KILLER ！\n\n🐶 作者: CassianVale\n",
        icon=icon_path,
        buttons=buttons
    )

    # 检查并尝试获取游戏目录
    for game_config in monitor.game_configs:
        if not game_config.game_dir:
            logger.info(f"尝试自动获取 {game_config.name} 游戏目录")
            # 尝试查找已运行的启动器进程
            launcher_proc = monitor.is_process_running(game_config.launcher)
            if launcher_proc:
                monitor.get_game_directory(game_config, launcher_proc)
            else:
                logger.info(f"{game_config.name} 启动器未运行，等待启动后自动获取游戏目录")

    # 启动已启用的游戏监控线程
    for game_config in monitor.game_configs:
        if game_config.enabled:
            monitor.start_monitor_thread(game_config)

    # 运行托盘图标 (这会阻塞主线程)
    tray_icon.run()

    logger.info("🔴 ACE-KILLER 程序已终止！")


if __name__ == "__main__":

    # 单实例检查
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\ACE-KILLER_MUTEX")
    if ctypes.windll.kernel32.GetLastError() == 183:
        logger.warning("程序已经在运行中，无法启动多个实例！")
        sys.exit(0)

    main()
