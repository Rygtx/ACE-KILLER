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
from ui.tray_icon import create_tray_icon


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
    
    # 设置日志系统
    setup_logger(
        config_manager.log_dir,
        config_manager.log_retention_days,
        config_manager.log_rotation
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
    
    # 创建并运行系统托盘图标
    tray_icon = create_tray_icon(monitor, icon_path)
    
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
    monitor.start_all_enabled_monitors()
    
    try:
        # 运行托盘图标 (这会阻塞主线程)
        tray_icon.run()
    except KeyboardInterrupt:
        # 处理键盘中断
        pass
    finally:
        # 停止所有线程
        monitor.stop_all_monitors()
        # 设置通知线程停止事件
        stop_event.set()
        # 等待通知线程结束
        notification_thread_obj.join(timeout=1.0)
        
    logger.info("🔴 ACE-KILLER 程序已终止！")


if __name__ == "__main__":
    main()
