#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统托盘界面模块
"""

import os
import subprocess
from PIL import Image
from pystray import MenuItem, Menu, Icon
from loguru import logger
from utils.notification import send_notification
from core.system_utils import enable_auto_start, disable_auto_start


def get_status_info(monitor):
    """
    获取程序状态信息
    
    Args:
        monitor: 进程监控器对象
        
    Returns:
        str: 状态信息文本
    """
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
    
    status_lines.append("\n⚙️ 系统设置：")
    status_lines.append("  🔔 通知状态：" + ("开启" if monitor.show_notifications else "关闭"))
    status_lines.append(f"  🔁 开机自启：{'开启' if monitor.auto_start else '关闭'}")
    status_lines.append(f"  📁 配置目录：{monitor.config_manager.config_dir}")
    status_lines.append(f"  📝 日志目录：{monitor.config_manager.log_dir}")
    status_lines.append(f"  ⏱️ 日志保留：{monitor.config_manager.log_retention_days}天")
    
    return "\n".join(status_lines)


def create_tray_icon(monitor, icon_path):
    """
    创建系统托盘图标
    
    Args:
        monitor: 进程监控器对象
        icon_path: 图标路径
        
    Returns:
        Icon: 系统托盘图标对象
    """
    # 载入图标
    image = Image.open(icon_path)
    
    # 定义菜单项动作函数
    def toggle_notifications():
        monitor.config_manager.show_notifications = not monitor.config_manager.show_notifications
        # 保存配置
        if monitor.config_manager.save_config():
            logger.info(f"通知状态已更改并保存: {'开启' if monitor.config_manager.show_notifications else '关闭'}")
        else:
            logger.warning(f"通知状态已更改但保存失败: {'开启' if monitor.config_manager.show_notifications else '关闭'}")
    
    def is_notifications_enabled(item):
        return monitor.show_notifications
    
    def toggle_auto_start():
        monitor.config_manager.auto_start = not monitor.config_manager.auto_start
        if monitor.config_manager.auto_start:
            enable_auto_start()
        else:
            disable_auto_start()
        # 保存配置
        if monitor.config_manager.save_config():
            logger.info(f"开机自启状态已更改并保存: {'开启' if monitor.config_manager.auto_start else '关闭'}")
        else:
            logger.warning(f"开机自启状态已更改但保存失败: {'开启' if monitor.config_manager.auto_start else '关闭'}")
    
    def is_auto_start_enabled(item):
        return monitor.auto_start
    
    def show_status():
        status = get_status_info(monitor)
        send_notification(
            title="ACE-KILLER 状态",
            message=status,
            icon_path=icon_path
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
                monitor.config_manager.save_config()
            
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
            if os.path.exists(monitor.config_manager.config_dir):
                subprocess.Popen(f'explorer "{monitor.config_manager.config_dir}"')
                logger.info(f"已打开配置目录: {monitor.config_manager.config_dir}")
            else:
                # 如果目录不存在，尝试创建
                os.makedirs(monitor.config_manager.config_dir, exist_ok=True)
                subprocess.Popen(f'explorer "{monitor.config_manager.config_dir}"')
                logger.info(f"已创建并打开配置目录: {monitor.config_manager.config_dir}")
        except Exception as e:
            logger.error(f"打开配置目录失败: {str(e)}")
    
    def exit_app():
        monitor.running = False
        monitor.stop_all_monitors()
        tray_icon.stop()
    
    # 创建菜单
    menu = Menu(
        MenuItem('显示状态', show_status),
        MenuItem('启动Windows通知', toggle_notifications, checked=is_notifications_enabled),
        MenuItem('开机自启', toggle_auto_start, checked=is_auto_start_enabled),
        Menu.SEPARATOR,
        MenuItem('游戏监控', Menu(*game_menu_items)),
        Menu.SEPARATOR,
        MenuItem('打开配置目录', open_config_dir),
        Menu.SEPARATOR,
        MenuItem('退出', exit_app)
    )
    
    # 创建托盘图标
    tray_icon = Icon("ace-killer", image, "ACE-KILLER", menu)
    
    return tray_icon 