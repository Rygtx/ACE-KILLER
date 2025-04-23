#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置管理模块
"""

import os
import yaml
from loguru import logger
from models.game_config import GameConfig
from core.system_utils import check_auto_start, enable_auto_start, disable_auto_start


class ConfigManager:
    """配置管理类"""
    
    def __init__(self):
        """初始化配置管理器"""
        self.config_dir = os.path.join(os.path.expanduser("~"), ".ace-killer")
        self.log_dir = os.path.join(self.config_dir, "logs")
        self.config_file = os.path.join(self.config_dir, "config.yaml")
        
        # 应用设置
        self.show_notifications = True  # Windows通知开关默认值
        self.auto_start = False  # 开机自启动开关默认值
        self.log_retention_days = 7  # 默认日志保留天数
        self.log_rotation = "1 day"  # 默认日志轮转周期
        self.game_configs = []  # 游戏配置列表
        
        # 确保配置目录存在
        self._ensure_directories()
        
        # 加载配置文件
        self.load_config()
    
    def _ensure_directories(self):
        """确保配置和日志目录存在"""
        # 确保配置目录存在
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
                logger.info(f"已创建配置目录: {self.config_dir}")
            except Exception as e:
                logger.error(f"创建配置目录失败: {str(e)}")
        
        # 确保日志目录存在
        if not os.path.exists(self.log_dir):
            try:
                os.makedirs(self.log_dir)
                logger.info(f"已创建日志目录: {self.log_dir}")
            except Exception as e:
                logger.error(f"创建日志目录失败: {str(e)}")
    
    def load_config(self):
        """
        加载配置文件
        
        Returns:
            bool: 是否加载成功
        """
        default_config = {
            'notifications': {
                'enabled': True
            },
            'logging': {
                'retention_days': 7,
                'rotation': '1 day'
            },
            'application': {
                'auto_start': False
            },
            'games': [
                {
                    'name': '无畏契约',
                    'launcher': '无畏契约登录器.exe',
                    'main_game': 'VALORANT-Win64-Shipping.exe',
                    'enabled': True
                },
                {
                    "name": "三角洲行动",
                    "launcher": "delta_force_launcher.exe",
                    "main_game": "DeltaForceClient-Win64-Shipping.exe",
                    "enabled": False,
                }
            ]
        }
        
        # 如果配置文件存在，则读取
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                # 如果配置文件为空或无效，使用默认配置
                if not config_data:
                    config_data = default_config
                    logger.warning("配置文件为空或无效，将使用默认配置")
                
                # 读取通知设置
                if 'notifications' in config_data and 'enabled' in config_data['notifications']:
                    self.show_notifications = bool(config_data['notifications']['enabled'])
                    logger.info(f"已从配置文件加载通知设置: {self.show_notifications}")
                
                # 读取日志设置
                if 'logging' in config_data:
                    if 'retention_days' in config_data['logging']:
                        self.log_retention_days = int(config_data['logging']['retention_days'])
                    if 'rotation' in config_data['logging']:
                        self.log_rotation = config_data['logging']['rotation']
                
                # 读取开机自启设置
                if 'application' in config_data and 'auto_start' in config_data['application']:
                    self.auto_start = bool(config_data['application']['auto_start'])
                    # 检查实际注册表状态与配置是否一致
                    actual_auto_start = check_auto_start()
                    if self.auto_start != actual_auto_start:
                        logger.warning(
                            f"开机自启配置与实际状态不一致，配置为:{self.auto_start}，实际为:{actual_auto_start}，将以配置为准")
                    
                    # 确保注册表状态与配置一致
                    if self.auto_start:
                        enable_auto_start()
                    else:
                        disable_auto_start()
                    
                    logger.info(f"已从配置文件加载开机自启设置: {self.auto_start}")
                else:
                    # 如果配置中没有自启设置，检查注册表中是否已设置
                    if check_auto_start():
                        # 如果注册表中已设置，则更新配置
                        self.auto_start = True
                        logger.info("检测到注册表中已设置开机自启，已更新配置")
                
                # 加载游戏配置
                self._load_game_configs(config_data)
                
                logger.info("配置文件加载成功")
                return True
            except Exception as e:
                logger.error(f"加载配置文件失败: {str(e)}")
                # 使用默认配置
                self._create_default_config(default_config)
                return False
        else:
            # 如果配置文件不存在，则创建默认配置文件
            logger.info("配置文件不存在，将创建默认配置文件")
            self._create_default_config(default_config)
            return True
    
    def _load_game_configs(self, config_data):
        """
        从配置数据中加载游戏配置
        
        Args:
            config_data (dict): 配置数据字典
        """
        self.game_configs.clear()
        if 'games' in config_data and isinstance(config_data['games'], list):
            for game_data in config_data['games']:
                if all(k in game_data for k in ['name', 'launcher', 'main_game', 'enabled']):
                    game_config = GameConfig(
                        name=game_data['name'],
                        launcher=game_data['launcher'],
                        main_game=game_data['main_game'],
                        enabled=game_data['enabled']
                    )
                    self.game_configs.append(game_config)
            
            logger.info(f"已从配置文件加载 {len(self.game_configs)} 个游戏配置")
    
    def _create_default_config(self, default_config):
        """
        创建默认配置文件
        
        Args:
            default_config (dict): 默认配置数据
        """
        try:
            # 使用默认配置
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            
            # 从默认配置中加载设置
            self.show_notifications = default_config['notifications']['enabled']
            self.log_retention_days = default_config['logging']['retention_days']
            self.log_rotation = default_config['logging']['rotation']
            self.auto_start = default_config['application']['auto_start']
            
            # 加载默认游戏配置
            self._load_game_configs(default_config)
            
            logger.info("已创建并加载默认配置")
        except Exception as e:
            logger.error(f"创建默认配置文件失败: {str(e)}")
    
    def save_config(self):
        """
        保存配置到文件
        
        Returns:
            bool: 保存是否成功
        """
        try:
            # 构建配置数据
            config_data = {
                'notifications': {
                    'enabled': self.show_notifications
                },
                'logging': {
                    'retention_days': self.log_retention_days,
                    'rotation': self.log_rotation
                },
                'application': {
                    'auto_start': self.auto_start
                },
                'games': []
            }
            
            # 添加游戏配置
            for game_config in self.game_configs:
                game_data = {
                    'name': game_config.name,
                    'launcher': game_config.launcher,
                    'main_game': game_config.main_game,
                    'enabled': game_config.enabled
                }
                config_data['games'].append(game_data)
            
            # 保存到文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            logger.info("配置已保存")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False
    
    def add_game_config(self, name, launcher, main_game, enabled=True):
        """
        添加新的游戏配置
        
        Args:
            name (str): 游戏名称
            launcher (str): 启动器进程名
            main_game (str): 主游戏进程名
            enabled (bool): 是否启用监控
            
        Returns:
            GameConfig: 新添加的游戏配置对象
        """
        game_config = GameConfig(name, launcher, main_game, enabled)
        self.game_configs.append(game_config)
        self.save_config()
        return game_config
    
    def remove_game_config(self, name):
        """
        删除游戏配置
        
        Args:
            name (str): 游戏名称
            
        Returns:
            bool: 是否成功删除
        """
        for i, config in enumerate(self.game_configs):
            if config.name == name:
                self.game_configs.pop(i)
                self.save_config()
                return True
        return False
    
    def get_game_config(self, name):
        """
        通过名称获取游戏配置
        
        Args:
            name (str): 游戏名称
            
        Returns:
            GameConfig or None: 游戏配置对象，未找到则返回None
        """
        for config in self.game_configs:
            if config.name == name:
                return config
        return None 