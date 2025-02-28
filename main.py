#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ctypes
import os
import sys
import time
import psutil
import win32process
import win32con
import win32api
import threading
from loguru import logger
import pystray
from PIL import Image
from winotify import Notification, audio
import queue
import subprocess
import configparser
import datetime
import winreg


class GameProcessMonitor:
    def __init__(self):
        self.launcher_name = "无畏契约登录器.exe"
        self.main_game_name = "VALORANT-Win64-Shipping.exe"
        self.anticheat_name = "ACE-Tray.exe"
        self.scanprocess_name = "SGuard64.exe"
        self.running = True     # 监控线程运行标记
        self.main_game_running = False  # 游戏主进程是否运行中标记
        self.process_cache = {}
        self.cache_timeout = 5
        self.last_cache_refresh = 0
        self.anticheat_killed = False   # 终止ACE进程标记
        self.scanprocess_optimized = False  # 优化SGuard64进程标记
        self.config_dir = os.path.join(os.path.expanduser("~"), ".ace_kill")  # 配置目录
        self.log_dir = os.path.join(self.config_dir, "log")  # 日志目录
        self.config_file = os.path.join(self.config_dir, "config.ini")  # 配置文件路径
        self.config = configparser.ConfigParser()
        self.show_notifications = True  # Windows通知开关默认值
        self.auto_start = False  # 开机自启动开关默认值
        self.message_queue = queue.Queue()  # 消息队列，用于在线程间传递状态信息
        
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
            handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, os.getpid())
            win32process.SetPriorityClass(handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass
    
    # 配置日志系统
    def setup_logger(self):
        # 移除默认的日志处理器
        logger.remove()
        
        # 获取当前日期作为日志文件名的一部分
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(self.log_dir, f"ace_kill_{today}.log")
        
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
            
    # 加载配置文件
    def load_config(self):
        # 默认配置
        default_config = {
            'Notifications': {
                'enabled': 'true'
            },
            'Logging': {
                'retention_days': '7',
                'rotation': '1 day'
            },
            'Application': {
                'auto_start': 'false'
            }
        }
        
        # 如果配置文件存在，则读取
        if os.path.exists(self.config_file):
            try:
                self.config.read(self.config_file, encoding='utf-8')
                # 读取通知设置
                if self.config.has_section('Notifications') and self.config.has_option('Notifications', 'enabled'):
                    self.show_notifications = self.config.getboolean('Notifications', 'enabled')
                    logger.info(f"已从配置文件加载通知设置: {self.show_notifications}")
                
                # 读取日志设置
                if self.config.has_section('Logging'):
                    if self.config.has_option('Logging', 'retention_days'):
                        self.log_retention_days = self.config.getint('Logging', 'retention_days')
                    if self.config.has_option('Logging', 'rotation'):
                        self.log_rotation = self.config.get('Logging', 'rotation')
                
                # 读取开机自启设置
                if self.config.has_section('Application') and self.config.has_option('Application', 'auto_start'):
                    self.auto_start = self.config.getboolean('Application', 'auto_start')
                    # 检查实际注册表状态与配置是否一致
                    actual_auto_start = self.check_auto_start()
                    if self.auto_start != actual_auto_start:
                        logger.warning(f"开机自启配置与实际状态不一致，配置为:{self.auto_start}，实际为:{actual_auto_start}，将以配置为准")
                    
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
                    else:
                        self.auto_start = False
                
                # 如果没有完整的配置项，则补充默认配置
                self.ensure_config_complete(default_config)
            except Exception as e:
                logger.error(f"读取配置文件失败: {str(e)}")
                # 配置文件可能损坏，创建默认配置
                self.save_default_config(default_config)
        else:
            # 配置文件不存在，创建默认配置
            self.save_default_config(default_config)
    
    # 确保配置完整
    def ensure_config_complete(self, default_config):
        config_updated = False
        
        # 检查并补充缺失的配置节和选项
        for section, options in default_config.items():
            if not self.config.has_section(section):
                self.config.add_section(section)
                config_updated = True
            
            for option, value in options.items():
                if not self.config.has_option(section, option):
                    self.config.set(section, option, value)
                    config_updated = True
        
        # 如果有更新，保存配置
        if config_updated:
            try:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    self.config.write(f)
                logger.info("已补充缺失的配置项")
            except Exception as e:
                logger.error(f"补充配置项失败: {str(e)}")
    
    # 保存默认配置
    def save_default_config(self, default_config):
        try:
            # 创建默认配置
            self.config.clear()
            for section, options in default_config.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                for option, value in options.items():
                    self.config.set(section, option, value)
            
            # 保存配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            # 更新内存中的设置
            if self.config.has_section('Notifications') and self.config.has_option('Notifications', 'enabled'):
                self.show_notifications = self.config.getboolean('Notifications', 'enabled')
            
            if self.config.has_section('Logging'):
                if self.config.has_option('Logging', 'retention_days'):
                    self.log_retention_days = self.config.getint('Logging', 'retention_days')
                if self.config.has_option('Logging', 'rotation'):
                    self.log_rotation = self.config.get('Logging', 'rotation')
            
            if self.config.has_section('Application') and self.config.has_option('Application', 'auto_start'):
                self.auto_start = self.config.getboolean('Application', 'auto_start')
            
            logger.info(f"已创建默认配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"创建默认配置文件失败: {str(e)}")
    
    # 保存配置
    def save_config(self):
        try:
            # 确保配置节存在
            if not self.config.has_section('Notifications'):
                self.config.add_section('Notifications')
            if not self.config.has_section('Logging'):
                self.config.add_section('Logging')
            if not self.config.has_section('Application'):
                self.config.add_section('Application')
            
            # 更新通知设置
            self.config.set('Notifications', 'enabled', str(self.show_notifications).lower())
            
            # 更新日志设置
            self.config.set('Logging', 'retention_days', str(self.log_retention_days))
            self.config.set('Logging', 'rotation', self.log_rotation)
            
            # 更新开机自启设置
            self.config.set('Application', 'auto_start', str(self.auto_start).lower())
            
            # 保存配置文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
                
            logger.info(f"已保存配置到: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {str(e)}")
            return False

    # 刷新进程缓存，确保缓存中的进程信息是最新的
    def refresh_process_cache(self, force=False):
        current_time = time.time()
        if force or (current_time - self.last_cache_refresh) >= self.cache_timeout:
            self.process_cache.clear()
            for proc in psutil.process_iter(['pid', 'name'], ad_value=None):
                try:
                    if proc.info['name']:
                        self.process_cache[proc.info['name'].lower()] = proc
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            self.last_cache_refresh = current_time
            
    # 检查进程是否在运行
    def is_process_running(self, process_name):
        process_name_lower = process_name.lower()
        
        if process_name_lower in self.process_cache:
            proc = self.process_cache[process_name_lower]
            try:
                if proc.is_running():
                    return proc
                else:
                    del self.process_cache[process_name_lower]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                del self.process_cache[process_name_lower]
                
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'].lower() == process_name_lower:
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
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, proc.pid)
                win32process.SetPriorityClass(handle, win32process.IDLE_PRIORITY_CLASS)
                
                cores = psutil.cpu_count(logical=True)
                if cores > 0:
                    small_core = cores - 1
                    proc.cpu_affinity([small_core])
                    logger.info(f"优化进程: {process_name}")
                    return True
            except Exception as e:
                logger.error(f"优化进程失败: {str(e)}")
        return False

    # 监控游戏主进程
    def monitor_main_game(self):
        check_counter = 0
        launcher_running = False  # Valorant登录器进程是否运行中标记
        
        # 循环监控游戏主进程和登录器进程
        while self.running:
            if check_counter % 10 == 0:
                self.refresh_process_cache()
            check_counter += 1
            
            # 检测游戏主进程
            main_proc = self.is_process_running(self.main_game_name)
            
            if main_proc and not self.main_game_running:
                self.main_game_running = True
                self.add_message("检测到游戏主进程启动")
                logger.info("检测到游戏主进程启动")
                self.refresh_process_cache(force=True)
                self.wait_and_kill_process(self.anticheat_name)
                self.wait_and_optimize_process(self.scanprocess_name)
                
            elif not main_proc and self.main_game_running:
                self.main_game_running = False
                self.anticheat_killed = False
                self.scanprocess_optimized = False
                self.add_message("游戏主进程已关闭")
                logger.info("游戏主进程已关闭")

            # 检测登录器进程
            launcher_proc = self.is_process_running(self.launcher_name)
            
            # 登录器启动状态检测
            if launcher_proc and not launcher_running:
                launcher_running = True
                self.add_message(f"检测到Valorant登录器正在运行")
                logger.info(f"检测到Valorant登录器正在运行，PID: {launcher_proc.pid}")
            
            # 登录器关闭状态检测
            elif not launcher_proc and launcher_running:
                launcher_running = False
                self.add_message(f"Valorant登录器已关闭")
                logger.info(f"Valorant登录器已关闭")
                
                # 等待登录器可能的重启
                wait_start = time.time()
                logger.info("等待Valorant登录器重启中，每5秒刷新进程缓存...")
                while time.time() - wait_start < 30 and self.running:
                    time.sleep(5)
                    self.refresh_process_cache(force=True)
                    launcher_check = self.is_process_running(self.launcher_name)
                    if launcher_check:
                        self.add_message(f"Valorant登录器已重启")
                        logger.info(f"Valorant登录器已重启，PID: {launcher_check.pid}")
                        launcher_running = True
                        break

            # 定期记录登录器状态
            elif launcher_proc and launcher_running and check_counter % 60 == 0:  # 大约每3分钟记录一次
                logger.info(f"Valorant登录器运行中，PID: {launcher_proc.pid}, CPU: {launcher_proc.cpu_percent()}%, 内存: {launcher_proc.memory_info().rss / 1024 / 1024:.2f}MB")
            
            time.sleep(3)
            
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

    # 获取程序完整路径
    def get_program_path(self):
        if getattr(sys, 'frozen', False):
            # PyInstaller创建的exe
            return sys.executable
        else:
            # 直接运行的python脚本
            return os.path.abspath(sys.argv[0])
    
    # 检查是否设置了开机自启
    def check_auto_start(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            try:
                value, _ = winreg.QueryValueEx(key, "VALORANT_ACE_KILLER")
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
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            program_path = self.get_program_path()
            winreg.SetValueEx(key, "VALORANT_ACE_KILLER", 0, winreg.REG_SZ, f'"{program_path}"')
            winreg.CloseKey(key)
            logger.info("已设置开机自启")
            return True
        except Exception as e:
            logger.error(f"设置开机自启失败: {str(e)}")
            return False
    
    # 取消开机自启
    def disable_auto_start(self):
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, "VALORANT_ACE_KILLER")
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
    
    if monitor.main_game_running:
        status_lines.append("🎮 游戏主程序：运行中")
        if monitor.anticheat_killed:
            status_lines.append("✅ ACE进程：已终止")
        else:
            status_lines.append("❓ ACE进程：未处理")
            
        if monitor.scanprocess_optimized:
            status_lines.append("✅ SGuard64进程：已优化")
        else:
            status_lines.append("❓ SGuard64进程：未处理")
    else:
        status_lines.append("🎮 游戏主程序：未运行")
    
    status_lines.append("🔔 通知状态：" + ("开启" if monitor.show_notifications else "关闭"))
    status_lines.append(f"📁 配置目录：{monitor.config_dir}")
    status_lines.append(f"📝 日志目录：{monitor.log_dir}")
    status_lines.append(f"⏱️ 日志保留：{monitor.log_retention_days}天，轮转：{monitor.log_rotation}")
    status_lines.append(f"🔁 开机自启：{'开启' if monitor.auto_start else '关闭'}")
    
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
        toast = Notification(
            app_id="VALORANT ACE KILLER",
            title="VALORANT ACE KILLER 状态",
            msg=status,
            icon=icon_path,
            duration="short"
        )
        toast.show()
        logger.info("已显示状态信息")
        
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
    menu = (
        pystray.MenuItem('显示状态', show_status),
        pystray.MenuItem('开启通知', toggle_notifications, checked=is_notifications_enabled),
        pystray.MenuItem('开机自启', toggle_auto_start, checked=is_auto_start_enabled),
        pystray.MenuItem('打开配置目录', open_config_dir),
        pystray.MenuItem('退出程序', exit_app)
    )
    
    # 创建托盘图标
    tray_icon = pystray.Icon("valorant_ace_killer", image, "VALORANT ACE KILLER", menu)
    
    return tray_icon

# 通知处理线程
def notification_thread(monitor, icon_path):
    while monitor.running:
        try:
            # 获取消息，最多等待1秒
            message = monitor.message_queue.get(timeout=1)
            toast = Notification(
                app_id="VALORANT ACE KILLER",
                title="VALORANT ACE KILLER",
                msg=message,
                icon=icon_path,
                duration="short"
            )
            toast.set_audio(audio.Default, loop=False)
            toast.show()
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
    logger.info("🟩 VALORANT ACE KILLER 程序已启动！")
    
    monitor_thread = threading.Thread(target=monitor.monitor_main_game)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 初始化通知组件
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'favicon.ico')
    
    # 创建通知处理线程
    notification_thread_obj = threading.Thread(
        target=notification_thread, 
        args=(monitor, icon_path)
    )
    notification_thread_obj.daemon = True
    notification_thread_obj.start()
    
    # 创建并运行系统托盘图标
    tray_icon = create_tray_icon(monitor, icon_path)
    
    # 显示欢迎通知
    toast = Notification(
        app_id="VALORANT ACE KILLER",
        title="VALORANT ACE KILLER 已启动",
        msg=f"程序现在运行在系统托盘，点击图标可查看菜单\n配置目录: {monitor.config_dir}",
        icon=icon_path,
        duration="short"
    )
    toast.set_audio(audio.Default, loop=False)
    toast.show()
    
    # 运行托盘图标 (这会阻塞主线程)
    tray_icon.run()
    
    logger.info("🔴 VALORANT ACE KILLER 程序已终止！")

if __name__ == "__main__":

    # 单实例检查
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\VALORANT_ACE_KILL_MUTEX")
    if ctypes.windll.kernel32.GetLastError() == 183:
        logger.warning("程序已经在运行中，无法启动多个实例！")
        sys.exit(0)
        
    main()
