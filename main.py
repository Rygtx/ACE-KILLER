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

        # 设置自身进程优先级
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, os.getpid())
            win32process.SetPriorityClass(handle, win32process.BELOW_NORMAL_PRIORITY_CLASS)
        except Exception:
            pass

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
                logger.info("检测到游戏主进程启动")
                self.refresh_process_cache(force=True)
                self.wait_and_kill_process(self.anticheat_name)
                self.wait_and_optimize_process(self.scanprocess_name)
                
            elif not main_proc and self.main_game_running:
                self.main_game_running = False
                self.anticheat_killed = False
                self.scanprocess_optimized = False
                logger.info("游戏主进程已关闭")

            # 检测登录器进程
            launcher_proc = self.is_process_running(self.launcher_name)
            
            # 登录器启动状态检测
            if launcher_proc and not launcher_running:
                launcher_running = True
                logger.info(f"检测到Valorant登录器 {self.launcher_name} 正在运行，PID: {launcher_proc.pid}")
            
            # 登录器关闭状态检测
            elif not launcher_proc and launcher_running:
                launcher_running = False
                logger.info(f"Valorant登录器 {self.launcher_name} 已关闭")
                
                # 等待登录器可能的重启
                wait_start = time.time()
                logger.info("等待Valorant登录器重启中，每5秒刷新进程缓存...")
                while time.time() - wait_start < 30 and self.running:
                    time.sleep(5)
                    print("2222")
                    self.refresh_process_cache(force=True)
                    launcher_check = self.is_process_running(self.launcher_name)
                    if launcher_check:
                        logger.info(f"Valorant登录器已重启，PID: {launcher_check.pid}")
                        launcher_running = True
                        break

            # 定期记录登录器状态
            elif launcher_proc and launcher_running and check_counter % 60 == 0:  # 大约每3分钟记录一次
                logger.info(f"Valorant登录器 {self.launcher_name} 运行中，PID: {launcher_proc.pid}, CPU: {launcher_proc.cpu_percent()}%, 内存: {launcher_proc.memory_info().rss / 1024 / 1024:.2f}MB")
            
            time.sleep(3)

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

def main():
    if not run_as_admin():
        return

    logger.info("🟩 VALORANT ACE KILLER 程序已启动！")
    
    # 创建监控线程
    monitor = GameProcessMonitor()
    monitor_thread = threading.Thread(target=monitor.monitor_main_game)
    monitor_thread.daemon = True
    monitor_thread.start()

    # 运行监控线程
    try:
        while monitor.running:
            time.sleep(5)
    except KeyboardInterrupt:
        monitor.running = False
        logger.info("🔴 VALORANT ACE KILLER 程序已终止！")

if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} - {level} - {message}")
    
    # 单实例检查
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\VALORANT_ACE_KILL_MUTEX")
    if ctypes.windll.kernel32.GetLastError() == 183:
        sys.exit(0)

    main()
