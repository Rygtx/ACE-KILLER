#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
通知系统模块
"""

import os
import sys
import queue
import threading
import time
from utils.logger import logger
from win11toast import notify


def send_notification(title, message, icon_path=None, buttons=None, silent=True):
    """
    发送Windows通知
    
    Args:
        title (str): 通知标题
        message (str): 通知内容
        icon_path (str, optional): 图标路径
        buttons (list, optional): 按钮列表
        silent (bool, optional): 是否静音通知
    """
    try:
        icon = None
        if icon_path and os.path.exists(icon_path):
            icon = {
                'src': icon_path,
                'placement': 'appLogoOverride'  # 方形icon
            }
        
        audio = {'silent': 'true'} if silent else None
        
        notify(
            app_id="ACE-KILLER",
            title=title,
            body=message,
            icon=icon,
            buttons=buttons,
            audio=audio
        )
        return True
    except Exception as e:
        logger.error(f"发送通知失败: {str(e)}")
        return False


def find_icon_path():
    """
    查找应用图标路径
    
    Returns:
        str or None: 找到的图标路径，如果未找到则返回None
    """
    # 查找图标文件
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    icon_paths = [
        # 标准开发环境路径
        os.path.join(base_path, 'assets', 'icon', 'favicon.ico'),
        # 打包环境路径
        os.path.join(os.path.dirname(sys.executable), 'favicon.ico')
    ]
    
    # 静默查找图标文件，使用第一个存在的路径
    for path in icon_paths:
        if os.path.exists(path):
            return path
    
    return None


def notification_thread(message_queue, icon_path=None, stop_event=None):
    """
    通知线程函数，从队列中获取消息并发送通知
    
    Args:
        message_queue (queue.Queue): 消息队列
        icon_path (str, optional): 图标路径
        stop_event (threading.Event, optional): 停止事件
    """
    logger.debug("通知线程已启动")
    
    # 如果未指定停止事件，则创建一个新的
    if stop_event is None:
        stop_event = threading.Event()
    
    while not stop_event.is_set():
        try:
            # 获取消息，最多等待0.5秒
            message = message_queue.get(timeout=0.5)
            
            # 发送通知
            send_notification(
                title="ACE-KILLER 消息通知",
                message=message,
                icon_path=icon_path
            )
            
            # 标记任务完成
            message_queue.task_done()
        except queue.Empty:
            # 队列为空，继续等待
            pass
        except Exception as e:
            logger.error(f"处理通知失败: {str(e)}")
            # 尝试短暂休眠以避免CPU占用过高
            time.sleep(0.1)
    
    logger.debug("通知线程已终止")


def create_notification_thread(message_queue, icon_path=None):
    """
    创建并启动通知线程
    
    Args:
        message_queue (queue.Queue): 消息队列
        icon_path (str, optional): 图标路径
        
    Returns:
        (threading.Thread, threading.Event): 线程对象和停止事件
    """
    # 如果未指定图标路径，则尝试查找
    if icon_path is None:
        icon_path = find_icon_path()
    
    # 创建停止事件
    stop_event = threading.Event()
    
    # 创建通知线程
    thread = threading.Thread(
        target=notification_thread,
        args=(message_queue, icon_path, stop_event),
        daemon=True
    )
    
    # 启动线程
    thread.start()
    
    return thread, stop_event 