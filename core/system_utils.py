#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
系统工具函数模块
"""

import ctypes
import os
import sys
import winreg
from loguru import logger


def run_as_admin():
    """
    判断是否以管理员权限运行，如果不是则尝试获取管理员权限
    
    Returns:
        bool: 是否以管理员权限运行
    """
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return False
    return True


def check_single_instance():
    """
    检查程序是否已经在运行，确保只有一个实例
    
    Returns:
        bool: 如果是首次运行返回True，否则返回False
    """
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\ACE-KILLER_MUTEX")
    if ctypes.windll.kernel32.GetLastError() == 183:
        logger.warning("程序已经在运行中，无法启动多个实例！")
        return False
    return True


def get_program_path():
    """
    获取程序完整路径
    
    Returns:
        str: 程序完整路径
    """
    if getattr(sys, 'frozen', False):
        return sys.executable
    else:
        # 直接运行的python脚本
        return os.path.abspath(sys.argv[0])


def check_auto_start(app_name="ACE-KILLER"):
    """
    检查是否设置了开机自启
    
    Args:
        app_name (str): 应用名称，默认为ACE-KILLER
    
    Returns:
        bool: 是否设置了开机自启
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 
                              0, winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            # 检查注册表中的路径是否与当前程序路径一致
            expected_path = f'"{get_program_path()}"'
            if value.lower() != expected_path.lower():
                logger.warning(f"注册表中的自启路径与当前程序路径不一致，将更新。注册表:{value}，当前:{expected_path}")
                # 需要更新为正确的路径
                return False
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception as e:
        logger.error(f"检查开机自启状态失败: {str(e)}")
        return False


def enable_auto_start(app_name="ACE-KILLER"):
    """
    设置开机自启
    
    Args:
        app_name (str): 应用名称，默认为ACE-KILLER
        
    Returns:
        bool: 操作是否成功
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 
                              0, winreg.KEY_SET_VALUE)
        program_path = get_program_path()
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{program_path}"')
        winreg.CloseKey(key)
        logger.debug("已设置开机自启")
        return True
    except Exception as e:
        logger.error(f"设置开机自启失败: {str(e)}")
        return False


def disable_auto_start(app_name="ACE-KILLER"):
    """
    取消开机自启
    
    Args:
        app_name (str): 应用名称，默认为ACE-KILLER
        
    Returns:
        bool: 操作是否成功
    """
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                              r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 
                              0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, app_name)
        except FileNotFoundError:
            # 注册表项不存在，无需删除
            pass
        winreg.CloseKey(key)
        logger.debug("已取消开机自启")
        return True
    except Exception as e:
        logger.error(f"取消开机自启失败: {str(e)}")
        return False 