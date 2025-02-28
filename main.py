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
        self.config_file = os.path.join(self.config_dir, "config.ini")  # 配置文件路径
        self.config = configparser.ConfigParser()
        self.show_notifications = True  # Windows通知开关默认值
        self.message_queue = queue.Queue()  # 消息队列，用于在线程间传递状态信息

        # 确保配置目录存在
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
                logger.info(f"已创建配置目录: {self.config_dir}")
            except Exception as e:
                logger.error(f"创建配置目录失败: {str(e)}")
                
        # 加载或创建配置文件
        self.load_config()

        # 设置自身进程优先级
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, os.getpid())
            win32process.SetPriorityClass(handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass
            
    # 加载配置文件
    def load_config(self):
        # 默认配置
        default_config = {
            'Notifications': {
                'enabled': 'true'
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
                else:
                    # 如果没有对应的配置项，则创建
                    self.save_default_config(default_config)
            except Exception as e:
                logger.error(f"读取配置文件失败: {str(e)}")
                # 配置文件可能损坏，创建默认配置
                self.save_default_config(default_config)
        else:
            # 配置文件不存在，创建默认配置
            self.save_default_config(default_config)
    
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
            
            logger.info(f"已创建默认配置文件: {self.config_file}")
        except Exception as e:
            logger.error(f"创建默认配置文件失败: {str(e)}")
    
    # 保存配置
    def save_config(self):
        try:
            # 确保配置节存在
            if not self.config.has_section('Notifications'):
                self.config.add_section('Notifications')
            
            # 更新通知设置
            self.config.set('Notifications', 'enabled', str(self.show_notifications).lower())
            
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
                logger.info(f"检测到Valorant登录器 {self.launcher_name} 正在运行，PID: {launcher_proc.pid}")
            
            # 登录器关闭状态检测
            elif not launcher_proc and launcher_running:
                launcher_running = False
                self.add_message(f"Valorant登录器已关闭")
                logger.info(f"Valorant登录器 {self.launcher_name} 已关闭")
                
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
                logger.info(f"Valorant登录器 {self.launcher_name} 运行中，PID: {launcher_proc.pid}, CPU: {launcher_proc.cpu_percent()}%, 内存: {launcher_proc.memory_info().rss / 1024 / 1024:.2f}MB")
            
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

    logger.info("🟩 VALORANT ACE KILLER 程序已启动！")
    
    # 创建监控线程
    monitor = GameProcessMonitor()
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
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}")
    
    # 单实例检查
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\VALORANT_ACE_KILL_MUTEX")
    if ctypes.windll.kernel32.GetLastError() == 183:
        logger.warning("程序已经在运行中，无法启动多个实例！")
        sys.exit(0)
        
    main()
