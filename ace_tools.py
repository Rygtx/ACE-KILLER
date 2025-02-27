import os
import sys
import time
import psutil
import win32process
import win32con
import win32api
import logging
import threading
import ctypes
from datetime import datetime
from win32gui import *
from win32api import *
from win32con import *
import win32gui_struct
import winreg
import win10toast
import pystray
from PIL import Image, ImageDraw
import io
import win32com.client

# 设置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='ace_tools_log.txt',
    filemode='a',
    encoding='utf-8'
)

class GameProcessMonitor:
    def __init__(self):
        self.launcher_name = "无畏契约登录器.exe"
        self.main_game_name = "VALORANT-Win64-Shipping.exe"
        self.anticheat_name = "ACE-Tray.exe"
        self.scanprocess_name = "SGuard64.exe"
        self.running = True
        self.main_game_running = False
        self.process_cache = {}
        self.cache_timeout = 5  # 进程缓存超时时间（秒）
        self.last_cache_refresh = 0
        
        # 处理状态跟踪
        self.anticheat_killed = False
        self.scanprocess_optimized = False
        
        # 初始化通知系统
        self.toaster = win10toast.ToastNotifier()
        
        # 设置当前进程为低优先级，减少自身资源占用
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, os.getpid())
            win32process.SetPriorityClass(handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass
        
    def create_tray_icon(self):
        """创建系统托盘图标"""
        # 创建一个简单的图标
        icon_image = self.create_icon_image()
        
        # 定义菜单项
        menu = (
            pystray.MenuItem('显示状态', self.show_status),
            pystray.MenuItem('退出', self.exit_app)
        )
        
        # 创建系统托盘图标
        self.icon = pystray.Icon("ace_tools", icon_image, "ACE工具", menu)
        return self.icon
    
    def create_icon_image(self):
        """创建一个简单的图标图像"""
        # 创建一个32x32的图像，白色背景
        image = Image.new('RGB', (32, 32), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)
        
        # 绘制一个简单的图形
        draw.rectangle([(8, 8), (24, 24)], fill=(255, 0, 0))
        
        return image
    
    def show_status(self, icon, item):
        """显示当前状态"""
        self.show_notification("ACE工具状态", 
                              f"游戏登录器: {'运行中' if self.is_process_running(self.launcher_name) else '未运行'}\n"
                              f"游戏主进程: {'运行中' if self.is_process_running(self.main_game_name) else '未运行'}\n"
                              f"ACE反作弊: {'已终止' if self.anticheat_killed else '未处理'}\n"
                              f"扫盘进程: {'已优化' if self.scanprocess_optimized else '未处理'}")
    
    def exit_app(self, icon, item):
        """退出应用"""
        self.running = False
        icon.stop()
    
    def show_notification(self, title, message, duration=5):
        """显示Windows通知"""
        try:
            self.toaster.show_toast(
                title,
                message,
                duration=duration,
                threaded=True
            )
            self.log(f"通知: {title} - {message}", "info")
        except Exception as e:
            self.log(f"显示通知失败: {str(e)}", "error")
        
    def log(self, message, level="info"):
        """记录日志并打印到控制台，但减少不必要的日志记录"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 仅在调试模式下打印到控制台
        if hasattr(sys, 'frozen') and not hasattr(sys, '_MEIPASS'):
            # 在打包的EXE中不打印到控制台
            pass
        else:
            print(f"{timestamp} - {message}")
        
        if level == "info":
            logging.info(message)
        elif level == "warning":
            logging.warning(message)
        elif level == "error":
            logging.error(message)
    
    def refresh_process_cache(self, force=False):
        """刷新进程缓存以提高性能"""
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
    
    def is_process_running(self, process_name):
        """检查指定进程是否正在运行（使用缓存提高性能）"""
        process_name_lower = process_name.lower()
        
        # 从缓存中查找进程
        if process_name_lower in self.process_cache:
            proc = self.process_cache[process_name_lower]
            try:
                # 验证进程是否还在运行
                if proc.is_running():
                    return proc
                else:
                    # 进程已终止，从缓存中移除
                    del self.process_cache[process_name_lower]
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                del self.process_cache[process_name_lower]
                
        # 缓存中没有找到，直接查找单个进程
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
    
    def kill_process(self, process_name):
        """终止指定名称的进程"""
        proc = self.is_process_running(process_name)
        if proc:
            try:
                proc.kill()
                self.log(f"已成功终止进程: {process_name}")
                self.show_notification("进程已终止", f"已成功终止进程: {process_name}")
                # 从缓存中移除已终止的进程
                if process_name.lower() in self.process_cache:
                    del self.process_cache[process_name.lower()]
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                self.log(f"无法终止进程: {process_name} - {str(e)}", "warning")
        else:
            self.log(f"进程未找到: {process_name}", "info")
        return False
    
    def set_process_priority_and_affinity(self, process_name):
        """设置进程优先级为空闲，并限制在一个小核心上运行"""
        proc = self.is_process_running(process_name)
        if proc:
            try:
                # 设置进程优先级为空闲
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, proc.pid)
                win32process.SetPriorityClass(handle, win32process.IDLE_PRIORITY_CLASS)
                
                # 获取系统CPU核心数量
                cores = psutil.cpu_count(logical=True)
                if cores > 0:
                    # 尝试识别小核心（非性能核心）
                    # 在大小核架构中，通常最后几个核心是小核心
                    # 这里我们假设最后一个是小核心
                    small_core = cores - 1
                    
                    # 仅使用一个核心
                    proc.cpu_affinity([small_core])
                    
                    success_msg = f"已将 {process_name} 设置为空闲优先级，并限制在核心 {small_core} 上运行"
                    self.log(success_msg)
                    self.show_notification("进程优化", success_msg)
                    return True
            except Exception as e:
                self.log(f"设置 {process_name} 优先级或亲和性时出错: {str(e)}", "error")
        else:
            self.log(f"进程未找到: {process_name}")
        return False
    
    def wait_for_launcher(self):
        """等待游戏登录器启动"""
        self.log("等待游戏登录器启动...")
        self.show_notification("ACE工具", "等待游戏登录器启动...")
        while self.running:
            if self.is_process_running(self.launcher_name):
                launcher_msg = f"检测到游戏登录器 {self.launcher_name} 已启动"
                self.log(launcher_msg)
                self.show_notification("游戏登录器已启动", launcher_msg)
                return True
            time.sleep(3)  # 每3秒检查一次，减少CPU使用
        return False
    
    def monitor_main_game(self):
        """监控游戏主进程"""
        check_counter = 0
        launcher_running = True
        
        while self.running:
            # 每10次循环刷新一次进程缓存，减少系统调用
            if check_counter % 10 == 0:
                self.refresh_process_cache()
            check_counter += 1
            
            # 检查主游戏进程
            main_proc = self.is_process_running(self.main_game_name)
            
            if main_proc and not self.main_game_running:
                self.main_game_running = True
                game_start_msg = f"检测到游戏主进程 {self.main_game_name} 已启动"
                self.log(game_start_msg)
                self.show_notification("游戏已启动", game_start_msg)
                
                # 强制刷新缓存以确保获取最新进程
                self.refresh_process_cache(force=True)
                
                # 等待并关闭ACE反作弊进程
                self.log("等待ACE反作弊进程启动...")
                self.wait_and_kill_process(self.anticheat_name)
                
                # 等待并设置扫盘进程优先级和亲和性
                self.log("等待扫盘进程启动...")
                self.wait_and_optimize_process(self.scanprocess_name)
                
            elif not main_proc and self.main_game_running:
                self.main_game_running = False
                # 重置处理状态
                self.anticheat_killed = False
                self.scanprocess_optimized = False
                game_close_msg = f"游戏主进程 {self.main_game_name} 已关闭"
                self.log(game_close_msg)
                self.show_notification("游戏已关闭", game_close_msg)
            
            # 检查游戏登录器是否还在运行
            launcher_proc = self.is_process_running(self.launcher_name)
            
            # 登录器状态变化检测
            if launcher_proc and not launcher_running:
                # 登录器重新启动
                launcher_running = True
                launcher_restart_msg = f"检测到游戏登录器 {self.launcher_name} 已重新启动"
                self.log(launcher_restart_msg)
                self.show_notification("游戏登录器已启动", launcher_restart_msg)
            elif not launcher_proc and launcher_running:
                # 登录器关闭
                launcher_running = False
                launcher_close_msg = f"游戏登录器 {self.launcher_name} 已关闭"
                self.log(launcher_close_msg)
                self.show_notification("游戏登录器已关闭", launcher_close_msg)
                
                # 不再立即退出，而是等待登录器可能的重新启动
                self.log("等待游戏登录器可能的重新启动...")
                
                # 设置等待计时器
                wait_start = time.time()
                wait_timeout = 30  # 等待30秒
                
                # 等待一段时间，看登录器是否重新启动
                while time.time() - wait_start < wait_timeout and self.running:
                    time.sleep(3)
                    self.refresh_process_cache(force=True)
                    if self.is_process_running(self.launcher_name):
                        # 登录器已重新启动，继续监控
                        break
                
                # 如果超时仍未重新启动，则退出监控
                if not self.is_process_running(self.launcher_name) and self.running:
                    self.log("游戏登录器未在预期时间内重新启动，退出监控")
                    self.show_notification("监控已停止", "游戏登录器未在预期时间内重新启动，退出监控")
                    self.running = False
                    break
            
            # 降低检查频率，减少CPU使用
            time.sleep(3)
    
    def start_monitoring(self):
        """开始监控进程"""
        self.log("ACE工具已启动")
        self.show_notification("ACE工具", "ACE工具已启动，正在监控游戏进程")
        
        # 重置状态变量
        self.running = True
        self.main_game_running = False
        self.anticheat_killed = False
        self.scanprocess_optimized = False
        
        # 首先等待游戏登录器启动
        if not self.is_process_running(self.launcher_name):
            if not self.wait_for_launcher():
                self.log("等待游戏登录器超时或被中断，退出程序")
                self.show_notification("ACE工具", "等待游戏登录器超时或被中断，退出程序")
                return
        else:
            # 如果登录器已经在运行，记录并通知
            launcher_msg = f"检测到游戏登录器 {self.launcher_name} 已在运行"
            self.log(launcher_msg)
            self.show_notification("游戏登录器已启动", launcher_msg)
        
        self.log("开始监控游戏进程...")
        
        # 启动游戏主进程监控线程
        monitor_thread = threading.Thread(target=self.monitor_main_game)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            # 简化主循环，减少系统资源使用
            while self.running:
                time.sleep(5)
                
        except KeyboardInterrupt:
            self.log("收到中断信号，脚本即将退出")
            
        except Exception as e:
            self.log(f"运行时发生错误: {str(e)}", "error")
            
        finally:
            self.log("ACE工具已停止")
            self.show_notification("ACE工具", "ACE工具已停止")
            
    def wait_and_kill_process(self, process_name, max_wait_time=60):
        """等待进程启动并终止它"""
        start_time = time.time()
        while self.running and time.time() - start_time < max_wait_time:
            proc = self.is_process_running(process_name)
            if proc:
                self.log(f"检测到 {process_name} 进程，正在终止...")
                if self.kill_process(process_name):
                    self.anticheat_killed = True
                    return True
            # 强制刷新缓存以确保获取最新进程
            self.refresh_process_cache(force=True)
            time.sleep(1)  # 每秒检查一次
        
        if time.time() - start_time >= max_wait_time:
            self.log(f"等待 {process_name} 进程超时")
        return False
    
    def wait_and_optimize_process(self, process_name, max_wait_time=60):
        """等待进程启动并优化它"""
        start_time = time.time()
        while self.running and time.time() - start_time < max_wait_time:
            proc = self.is_process_running(process_name)
            if proc:
                self.log(f"检测到 {process_name} 进程，正在优化...")
                if self.set_process_priority_and_affinity(process_name):
                    self.scanprocess_optimized = True
                    return True
            # 强制刷新缓存以确保获取最新进程
            self.refresh_process_cache(force=True)
            time.sleep(1)  # 每秒检查一次
        
        if time.time() - start_time >= max_wait_time:
            self.log(f"等待 {process_name} 进程超时")
        return False

def run_as_admin():
    """检查并请求管理员权限"""
    if not ctypes.windll.shell32.IsUserAnAdmin():
        # 重新以管理员权限启动
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return False
    return True

def create_startup_shortcut():
    """创建开机启动快捷方式"""
    try:
        startup_folder = os.path.join(
            os.environ["APPDATA"], 
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )
        shortcut_path = os.path.join(startup_folder, "ACE工具.lnk")
        
        # 如果快捷方式已存在，则不再创建
        if os.path.exists(shortcut_path):
            return
            
        # 获取当前可执行文件路径
        if hasattr(sys, 'frozen'):
            app_path = sys.executable
        else:
            app_path = os.path.abspath(sys.argv[0])
            
        # 创建快捷方式
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = app_path
        shortcut.WorkingDirectory = os.path.dirname(app_path)
        shortcut.Description = "ACE工具 - 游戏优化助手"
        shortcut.save()
        
        return True
    except Exception as e:
        logging.error(f"创建启动快捷方式失败: {str(e)}")
        return False

def main():
    """主函数"""
    # 检查管理员权限
    if not run_as_admin():
        return
        
    # 创建系统托盘图标
    monitor = GameProcessMonitor()
    icon = monitor.create_tray_icon()
    
    # 在单独的线程中启动监控
    monitor_thread = threading.Thread(target=monitor.start_monitoring)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 运行系统托盘图标（这会阻塞主线程）
    icon.run()
    
if __name__ == "__main__":
    # 导入这些模块在这里，避免循环导入
    import win32com.client
    
    # 检查是否需要创建开机启动快捷方式
    create_startup_shortcut()
    
    # 启动主程序，并在退出后重新启动
    while True:
        main()
        # 等待一段时间后重新启动
        time.sleep(5)
        logging.info("重新启动ACE工具...")