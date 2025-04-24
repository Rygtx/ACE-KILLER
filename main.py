#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ACE-KILLER主程序入口
"""

import os
import sys
import queue
from loguru import logger

# 导入自定义模块
from config.config_manager import ConfigManager
from core.process_monitor import GameProcessMonitor
from core.system_utils import run_as_admin, check_single_instance
from utils.logger import setup_logger
from utils.notification import find_icon_path, send_notification, create_notification_thread
from ui.main_window import create_gui


def main():
    """主程序入口函数"""
    # 检查管理员权限
    if not run_as_admin():
        return
    
    # 检查单实例运行
    if not check_single_instance():
        return
    
    # 创建配置管理器
    config_manager = ConfigManager()
    
    # 配置日志系统
    setup_logger(
        config_manager.log_dir,
        config_manager.log_retention_days,
        config_manager.log_rotation,
        config_manager.debug_mode  # 传递调试模式设置
    )
    
    # 创建进程监控器
    monitor = GameProcessMonitor(config_manager)
    
    # 现在日志系统已初始化，可以记录启动信息
    logger.info("🟩 ACE-KILLER 程序已启动！")
    
    # 查找图标文件
    icon_path = find_icon_path()
    
    # 创建通知线程
    notification_thread_obj, stop_event = create_notification_thread(
        monitor.message_queue,
        icon_path
    )
    
    # 创建并运行PySide6图形界面
    app, window = create_gui(monitor, icon_path)
    
    # 显示欢迎通知
    buttons = [
        {'activationType': 'protocol', 'arguments': 'https://github.com/cassianvale/ACE-KILLER', 'content': '访问项目地址'},
        {'activationType': 'protocol', 'arguments': 'https://github.com/cassianvale/ACE-KILLER/releases/latest', 'content': '获取最新版本'}
    ]
    
    send_notification(
        title="ACE-KILLER",
        message=f"🚀 启动成功！欢迎使用 ACE-KILLER ！\n\n🐶 作者: CassianVale\n",
        icon_path=icon_path,
        buttons=buttons,
        silent=False
    )
    
    # 启动已启用的游戏监控线程
    if any(game.enabled for game in monitor.game_configs):
        monitor.running = True  # 显式设置为True
        logger.info("监控程序已启动")
        monitor.start_all_enabled_monitors()
    else:
        monitor.running = False  # 显式设置为False
        logger.info("未启用任何游戏监控，不启动监控线程")
    
    try:
        # 显示窗口
        window.show()
        # 运行应用（这会阻塞主线程直到应用程序退出）
        sys.exit(app.exec())
    except KeyboardInterrupt:
        # 处理键盘中断
        pass
    finally:
        # 确保停止所有线程，唯一调用stop_all_monitors的地方
        if monitor.running:
            monitor.running = False
            # 停止所有游戏监控
            monitor.stop_all_monitors()
            
        # 设置通知线程停止事件
        stop_event.set()
        # 等待通知线程结束
        notification_thread_obj.join(timeout=1.0)
        
    logger.info("🔴 ACE-KILLER 程序已终止！")


if __name__ == "__main__":
    main()
