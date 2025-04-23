#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
游戏配置类模块
"""

class GameConfig:
    """游戏配置类，存储游戏相关信息"""
    
    def __init__(self, name: str, launcher: str, main_game: str, enabled: bool):
        """
        初始化游戏配置
        
        Args:
            name (str): 游戏名称
            launcher (str): 启动器进程名
            main_game (str): 主游戏进程名
            enabled (bool): 是否启用监控
        """
        self.name = name
        self.launcher = launcher
        self.main_game = main_game
        self.enabled = bool(enabled)
        self.monitor_thread = None
        self.main_game_running = False
        self.anticheat_handled = False
        self.scanprocess_handled = False 