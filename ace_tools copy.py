import os
import sys
import time
import psutil
import win32process
import win32con
import win32api
import logging
import threading
from datetime import datetime

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
        
    def log(self, message):
        """记录日志并打印到控制台"""
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}")
        logging.info(message)
        
    def is_process_running(self, process_name):
        """检查指定进程是否正在运行"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() == process_name.lower():
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return None
    
    def kill_process(self, process_name):
        """终止指定名称的进程"""
        proc = self.is_process_running(process_name)
        if proc:
            try:
                proc.kill()
                self.log(f"已成功终止进程: {process_name}")
                return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.log(f"无法终止进程: {process_name} - 权限被拒绝")
        else:
            self.log(f"进程未找到: {process_name}")
        return False
    
    def set_process_priority_and_affinity(self, process_name):
        """设置进程优先级为低，并限制在一个小核心上运行"""
        proc = self.is_process_running(process_name)
        if proc:
            try:
                # 设置进程优先级为低
                handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, False, proc.pid)
                win32process.SetPriorityClass(handle, win32process.IDLE_PRIORITY_CLASS)
                
                # 获取系统CPU核心数量
                cores = psutil.cpu_count(logical=True)
                if cores > 0:
                    # 假设最后一个核心是小核心(根据您的系统架构可能需要调整)
                    # 可以根据实际情况修改核心选择
                    small_core_mask = 1 << (cores - 1)  # 仅使用最后一个核心
                    proc.cpu_affinity([cores - 1])  # 设置亲和性为最后一个核心
                    
                    self.log(f"已将 {process_name} 设置为低优先级，并限制在核心 {cores-1} 上运行")
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
                self.log(f"设置 {process_name} 优先级或亲和性时出错: {str(e)}")
        else:
            self.log(f"进程未找到: {process_name}")
        return False
    
    def monitor_main_game(self):
        """监控游戏主进程"""
        while self.running:
            main_proc = self.is_process_running(self.main_game_name)
            
            if main_proc and not self.main_game_running:
                self.main_game_running = True
                self.log(f"检测到游戏主进程 {self.main_game_name} 已启动")
                
                # 关闭ACE反作弊进程
                self.log("尝试关闭ACE反作弊进程...")
                self.kill_process(self.anticheat_name)
                
                # 等待一段时间确保扫盘进程存在
                time.sleep(5)
                
                # 设置扫盘进程优先级和亲和性
                self.log("尝试设置扫盘进程优先级和CPU亲和性...")
                self.set_process_priority_and_affinity(self.scanprocess_name)
                
            elif not main_proc and self.main_game_running:
                self.main_game_running = False
                self.log(f"游戏主进程 {self.main_game_name} 已关闭")
            
            time.sleep(2)  # 每2秒检查一次
    
    def start_monitoring(self):
        """开始监控进程"""
        self.log("ACE工具已启动，开始监控游戏进程...")
        
        # 启动游戏主进程监控线程
        monitor_thread = threading.Thread(target=self.monitor_main_game)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        try:
            while self.running:
                # 检查游戏是否已关闭，如果游戏登录器关闭则退出脚本
                if not self.is_process_running(self.launcher_name):
                    self.log(f"游戏登录器 {self.launcher_name} 已关闭，脚本即将退出")
                    self.running = False
                    break
                
                time.sleep(5)  # 每5秒检查一次登录器状态
                
        except KeyboardInterrupt:
            self.log("收到中断信号，脚本即将退出")
            self.running = False
            
        except Exception as e:
            self.log(f"运行时发生错误: {str(e)}")
            
        finally:
            self.log("ACE工具已停止")
            
if __name__ == "__main__":
    monitor = GameProcessMonitor()
    monitor.start_monitoring()