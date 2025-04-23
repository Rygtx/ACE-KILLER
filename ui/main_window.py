#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySide6 GUI界面模块
"""

import os
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QCheckBox, QSystemTrayIcon, QMenu, 
    QListWidget, QListWidgetItem, QGroupBox, QTabWidget, QFrame,
    QMessageBox, QScrollArea, QStyle
)
from PySide6.QtCore import Qt, Signal, QSize, QObject, Slot, QTimer, QEvent
from PySide6.QtGui import QIcon, QPixmap, QColor, QAction
from loguru import logger

from utils.notification import send_notification
from core.system_utils import enable_auto_start, disable_auto_start


class GameListItem(QWidget):
    """游戏列表项组件"""
    
    statusChanged = Signal(str, bool)
    
    def __init__(self, game_name, enabled=False, parent=None):
        super().__init__(parent)
        self.game_name = game_name
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        self.checkbox = QCheckBox(game_name)
        self.checkbox.setChecked(enabled)
        self.checkbox.stateChanged.connect(self._on_state_changed)
        
        layout.addWidget(self.checkbox)
        layout.addStretch()
    
    def _on_state_changed(self, state):
        self.statusChanged.emit(self.game_name, bool(state))
    
    def set_checked(self, checked):
        """设置复选框状态，但不触发信号"""
        self.checkbox.blockSignals(True)
        self.checkbox.setChecked(checked)
        self.checkbox.blockSignals(False)


class MainWindow(QMainWindow):
    """主窗口"""
    
    configChanged = Signal()
    
    def __init__(self, monitor, icon_path=None):
        super().__init__()
        
        self.monitor = monitor
        self.icon_path = icon_path
        self.setup_ui()
        self.setup_tray()
        
        # 添加定时器，定期更新状态
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(3000)  # 每3秒更新一次
        
        # 初始加载设置
        self.load_settings()
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("ACE-KILLER")
        self.setMinimumSize(600, 500)
        
        if self.icon_path and os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))
        
        # 创建主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # 状态选项卡
        status_tab = QWidget()
        status_layout = QVBoxLayout(status_tab)
        
        # 状态信息框
        status_group = QGroupBox("程序状态")
        status_box_layout = QVBoxLayout()
        self.status_label = QLabel("加载中...")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignTop)
        self.status_label.setTextFormat(Qt.RichText)
        status_scroll = QScrollArea()
        status_scroll.setWidgetResizable(True)
        status_scroll.setWidget(self.status_label)
        status_box_layout.addWidget(status_scroll)
        status_group.setLayout(status_box_layout)
        status_layout.addWidget(status_group)
        
        # 游戏监控选项卡
        games_tab = QWidget()
        games_layout = QVBoxLayout(games_tab)
        
        # 游戏列表
        games_group = QGroupBox("游戏监控")
        games_box_layout = QVBoxLayout()
        self.games_list = QListWidget()
        games_box_layout.addWidget(self.games_list)
        games_group.setLayout(games_box_layout)
        games_layout.addWidget(games_group)
        
        # 设置选项卡
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        # 通知设置
        notify_group = QGroupBox("通知设置")
        notify_layout = QVBoxLayout()
        self.notify_checkbox = QCheckBox("启用Windows通知")
        self.notify_checkbox.stateChanged.connect(self.toggle_notifications)
        notify_layout.addWidget(self.notify_checkbox)
        notify_group.setLayout(notify_layout)
        settings_layout.addWidget(notify_group)
        
        # 启动设置
        startup_group = QGroupBox("启动设置")
        startup_layout = QVBoxLayout()
        self.startup_checkbox = QCheckBox("开机自启动")
        self.startup_checkbox.stateChanged.connect(self.toggle_auto_start)
        startup_layout.addWidget(self.startup_checkbox)
        startup_group.setLayout(startup_layout)
        settings_layout.addWidget(startup_group)
        
        # 添加操作按钮
        actions_group = QGroupBox("操作")
        actions_layout = QHBoxLayout()
        
        # 打开配置目录按钮
        self.config_dir_btn = QPushButton("打开配置目录")
        self.config_dir_btn.clicked.connect(self.open_config_dir)
        actions_layout.addWidget(self.config_dir_btn)
        
        # 检查更新按钮
        self.check_update_btn = QPushButton("检查更新")
        self.check_update_btn.clicked.connect(self.check_update)
        actions_layout.addWidget(self.check_update_btn)
        
        # 关于按钮
        self.about_btn = QPushButton("关于")
        self.about_btn.clicked.connect(self.show_about)
        actions_layout.addWidget(self.about_btn)
        
        actions_group.setLayout(actions_layout)
        settings_layout.addWidget(actions_group)
        
        # 添加空白占位
        settings_layout.addStretch()
        
        # 添加选项卡
        tabs.addTab(status_tab, "状态")
        tabs.addTab(games_tab, "游戏")
        tabs.addTab(settings_tab, "设置")
    
    def setup_tray(self):
        """设置系统托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        if self.icon_path and os.path.exists(self.icon_path):
            self.tray_icon.setIcon(QIcon(self.icon_path))
        else:
            # 使用系统预设图标
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 显示主窗口动作
        show_action = QAction("显示主窗口", self)
        show_action.triggered.connect(self.show_main_window)
        tray_menu.addAction(show_action)
        
        # 显示状态动作
        status_action = QAction("显示状态", self)
        status_action.triggered.connect(self.show_status)
        tray_menu.addAction(status_action)
        
        tray_menu.addSeparator()
        
        # 启用通知动作
        self.notify_action = QAction("启用通知", self)
        self.notify_action.setCheckable(True)
        self.notify_action.triggered.connect(self.toggle_notifications_from_tray)
        tray_menu.addAction(self.notify_action)
        
        # 开机自启动动作
        self.startup_action = QAction("开机自启动", self)
        self.startup_action.setCheckable(True)
        self.startup_action.triggered.connect(self.toggle_auto_start_from_tray)
        tray_menu.addAction(self.startup_action)
        
        tray_menu.addSeparator()
        
        # 游戏监控子菜单
        self.games_menu = QMenu("游戏监控")
        self.update_games_menu()  # 初始添加游戏菜单项
        tray_menu.addMenu(self.games_menu)
        
        tray_menu.addSeparator()
        
        # 打开配置目录动作
        config_dir_action = QAction("打开配置目录", self)
        config_dir_action.triggered.connect(self.open_config_dir)
        tray_menu.addAction(config_dir_action)
        
        tray_menu.addSeparator()
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.confirm_exit)
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()
        
        # 设置工具提示
        self.tray_icon.setToolTip("ACE-KILLER")
    
    def update_games_menu(self):
        """更新游戏监控子菜单"""
        self.games_menu.clear()
        
        # 清空游戏列表
        self.games_list.clear()
        
        # 添加所有游戏配置
        for game_config in self.monitor.game_configs:
            # 添加到GUI列表
            list_item = QListWidgetItem(self.games_list)
            game_widget = GameListItem(game_config.name, game_config.enabled)
            game_widget.statusChanged.connect(self.on_game_status_changed)
            list_item.setSizeHint(game_widget.sizeHint())
            self.games_list.addItem(list_item)
            self.games_list.setItemWidget(list_item, game_widget)
            
            # 添加到托盘菜单
            game_action = QAction(game_config.name, self)
            game_action.setCheckable(True)
            game_action.setChecked(game_config.enabled)
            game_action.setData(game_config.name)
            game_action.triggered.connect(self.toggle_game_from_tray)
            self.games_menu.addAction(game_action)
    
    def load_settings(self):
        """加载设置到UI"""
        # 阻塞信号避免双重触发
        self.blockSignals(True)
        
        # 更新通知设置
        self.notify_checkbox.setChecked(self.monitor.show_notifications)
        self.notify_action.setChecked(self.monitor.show_notifications)
        
        # 更新自启动设置
        self.startup_checkbox.setChecked(self.monitor.auto_start)
        self.startup_action.setChecked(self.monitor.auto_start)
        
        self.update_status()
        self.blockSignals(False)
    
    def update_status(self):
        """更新状态显示"""
        status_html = self.get_status_html()
        self.status_label.setText(status_html)
        
        # 更新游戏列表状态，避免重复触发事件
        for i in range(self.games_list.count()):
            item = self.games_list.item(i)
            widget = self.games_list.itemWidget(item)
            for game_config in self.monitor.game_configs:
                if game_config.name == widget.game_name:
                    widget.set_checked(game_config.enabled)
                    break
        
        # 更新托盘菜单游戏状态
        for action in self.games_menu.actions():
            game_name = action.data()
            for game_config in self.monitor.game_configs:
                if game_config.name == game_name:
                    action.blockSignals(True)
                    action.setChecked(game_config.enabled)
                    action.blockSignals(False)
                    break
    
    def get_status_html(self):
        """获取HTML格式的状态信息"""
        if not self.monitor:
            return "<p>程序未启动</p>"
        
        status_lines = []
        status_lines.append("<p style='color: green; font-weight: bold;'>🟢 监控程序运行中</p>" if self.monitor.running else "<p style='color: red; font-weight: bold;'>🔴 监控程序已停止</p>")
        
        # 检查是否有任何游戏在运行
        running_games = [game_config.name for game_config in self.monitor.game_configs 
                         if game_config.enabled and game_config.main_game_running]
        any_game_running = bool(running_games)
        
        # 检查反作弊和扫描进程状态
        anticheat_status = self._check_anticheat_status()
        scanprocess_status = self._check_scanprocess_status()
        
        if any_game_running:
            status_lines.append(f"<p>🎮 游戏主程序：<span style='color: green; font-weight: bold;'>运行中</span> ({', '.join(running_games)})</p>")
            status_lines.append(f"<p>{anticheat_status[0]} ACE进程：<span style='color: {anticheat_status[1]};'>{anticheat_status[2]}</span></p>")
            status_lines.append(f"<p>{scanprocess_status[0]} SGuard64进程：<span style='color: {scanprocess_status[1]};'>{scanprocess_status[2]}</span></p>")
        else:
            status_lines.append("<p>🎮 游戏主程序：<span style='color: gray;'>未运行</span></p>")
        
        status_lines.append("<p><b>⚙️ 系统设置：</b></p>")
        status_lines.append("<p>  🔔 通知状态：<span style='color: green;'>开启</span></p>" if self.monitor.show_notifications else "<p>  🔔 通知状态：<span style='color: gray;'>关闭</span></p>")
        status_lines.append(f"<p>  🔁 开机自启：<span style='color: green;'>开启</span></p>" if self.monitor.auto_start else "<p>  🔁 开机自启：<span style='color: gray;'>关闭</span></p>")
        status_lines.append(f"<p>  📁 配置目录：{self.monitor.config_manager.config_dir}</p>")
        status_lines.append(f"<p>  📝 日志目录：{self.monitor.config_manager.log_dir}</p>")
        status_lines.append(f"<p>  ⏱️ 日志保留：{self.monitor.config_manager.log_retention_days}天</p>")
        
        return "".join(status_lines)
    
    def _check_anticheat_status(self):
        """
        检查反作弊进程状态
        
        Returns:
            tuple: (图标, 颜色, 状态文本)
        """
        # 检查是否有任何游戏在运行
        any_game_running = any(game_config.main_game_running for game_config in self.monitor.game_configs 
                              if game_config.enabled)
        
        if not any_game_running:
            return "❓", "gray", "未检测"
            
        # 检查 ACE-Tray.exe 是否存在
        ace_proc = self.monitor.is_process_running(self.monitor.anticheat_name)
        
        # 如果反作弊进程不存在，且全局状态标记为已处理
        if not ace_proc and self.monitor.anticheat_killed:
            return "✅", "green", "已终止"
        
        # 如果反作弊进程不存在，但没有标记处理成功
        if not ace_proc:
            return "ℹ️", "blue", "未运行"
            
        # 如果反作弊进程存在，但已标记为处理过(说明即将被终止)
        if ace_proc and self.monitor.anticheat_killed:
            return "⏳", "orange", "处理中"
            
        # 反作弊进程存在，且未处理
        return "❗", "red", "需要处理"
    
    def _check_scanprocess_status(self):
        """
        检查扫描进程状态
        
        Returns:
            tuple: (图标, 颜色, 状态文本)
        """
        # 检查是否有任何游戏在运行
        any_game_running = any(game_config.main_game_running for game_config in self.monitor.game_configs 
                              if game_config.enabled)
        
        if not any_game_running:
            return "❓", "gray", "未检测"
            
        # 检查 SGuard64.exe 是否存在
        scan_proc = self.monitor.is_process_running(self.monitor.scanprocess_name)
        
        # 如果扫描进程不存在，且全局状态标记为已优化
        if not scan_proc and self.monitor.scanprocess_optimized:
            return "✅", "green", "已优化"
        
        # 如果扫描进程不存在，但没有标记处理成功
        if not scan_proc:
            return "ℹ️", "blue", "未运行"
            
        # 如果扫描进程存在，但已标记为处理过
        if scan_proc and self.monitor.scanprocess_optimized:
            # 验证是否真的优化了
            try:
                is_running, is_optimized = self.monitor.check_process_status(self.monitor.scanprocess_name)
                if is_running and is_optimized:
                    return "✅", "green", "已优化"
                else:
                    return "⏳", "orange", "优化中"
            except Exception:
                # 如果无法检查状态，显示处理中
                return "⏳", "orange", "优化中"
            
        # 扫描进程存在，且未处理
        return "❗", "red", "需要优化"
    
    @Slot()
    def toggle_notifications(self):
        """切换通知开关"""
        self.monitor.config_manager.show_notifications = self.notify_checkbox.isChecked()
        # 同步更新托盘菜单选项
        self.notify_action.blockSignals(True)
        self.notify_action.setChecked(self.monitor.config_manager.show_notifications)
        self.notify_action.blockSignals(False)
        # 保存配置
        if self.monitor.config_manager.save_config():
            logger.info(f"通知状态已更改并保存: {'开启' if self.monitor.config_manager.show_notifications else '关闭'}")
        else:
            logger.warning(f"通知状态已更改但保存失败: {'开启' if self.monitor.config_manager.show_notifications else '关闭'}")
    
    @Slot()
    def toggle_notifications_from_tray(self):
        """从托盘菜单切换通知开关"""
        self.monitor.config_manager.show_notifications = self.notify_action.isChecked()
        # 同步更新主窗口选项
        self.notify_checkbox.blockSignals(True)
        self.notify_checkbox.setChecked(self.monitor.config_manager.show_notifications)
        self.notify_checkbox.blockSignals(False)
        # 保存配置
        if self.monitor.config_manager.save_config():
            logger.info(f"通知状态已更改并保存: {'开启' if self.monitor.config_manager.show_notifications else '关闭'}")
        else:
            logger.warning(f"通知状态已更改但保存失败: {'开启' if self.monitor.config_manager.show_notifications else '关闭'}")
    
    @Slot()
    def toggle_auto_start(self):
        """切换开机自启动开关"""
        self.monitor.config_manager.auto_start = self.startup_checkbox.isChecked()
        # 同步更新托盘菜单选项
        self.startup_action.blockSignals(True)
        self.startup_action.setChecked(self.monitor.config_manager.auto_start)
        self.startup_action.blockSignals(False)
        
        # 修改注册表
        if self.monitor.config_manager.auto_start:
            enable_auto_start()
        else:
            disable_auto_start()
        
        # 保存配置
        if self.monitor.config_manager.save_config():
            logger.info(f"开机自启状态已更改并保存: {'开启' if self.monitor.config_manager.auto_start else '关闭'}")
        else:
            logger.warning(f"开机自启状态已更改但保存失败: {'开启' if self.monitor.config_manager.auto_start else '关闭'}")
    
    @Slot()
    def toggle_auto_start_from_tray(self):
        """从托盘菜单切换开机自启动开关"""
        self.monitor.config_manager.auto_start = self.startup_action.isChecked()
        # 同步更新主窗口选项
        self.startup_checkbox.blockSignals(True)
        self.startup_checkbox.setChecked(self.monitor.config_manager.auto_start)
        self.startup_checkbox.blockSignals(False)
        
        # 修改注册表
        if self.monitor.config_manager.auto_start:
            enable_auto_start()
        else:
            disable_auto_start()
        
        # 保存配置
        if self.monitor.config_manager.save_config():
            logger.info(f"开机自启状态已更改并保存: {'开启' if self.monitor.config_manager.auto_start else '关闭'}")
        else:
            logger.warning(f"开机自启状态已更改但保存失败: {'开启' if self.monitor.config_manager.auto_start else '关闭'}")
    
    @Slot(str, bool)
    def on_game_status_changed(self, game_name, enabled):
        """游戏监控状态改变处理函数"""
        for game_config in self.monitor.game_configs:
            if game_config.name == game_name:
                if game_config.enabled != enabled:
                    game_config.enabled = enabled
                    if enabled:
                        # 如果是从无启用游戏到有启用游戏，设置running为True
                        was_running = self.monitor.running
                        if not was_running:
                            self.monitor.running = True
                            logger.info("监控程序已启动")
                        
                        # 启用游戏监控
                        self.monitor.start_monitor_thread(game_config)
                    else:
                        # 停止该游戏的监控
                        self.monitor.stop_monitor_thread(game_config)
                        
                        # 检查是否还有其他启用的游戏
                        if not any(g.enabled for g in self.monitor.game_configs):
                            # 如果没有任何启用的游戏，重置监控器状态
                            logger.info("所有游戏监控已关闭")
                            self.monitor.running = False
                            self.monitor.anticheat_killed = False
                            self.monitor.scanprocess_optimized = False
                            logger.info("监控程序已停止")
                    
                    # 保存配置
                    self.monitor.config_manager.save_config()
                    
                    # 立即更新状态显示
                    self.update_status()
                break
        
        # 更新托盘菜单
        for action in self.games_menu.actions():
            if action.data() == game_name:
                action.blockSignals(True)
                action.setChecked(enabled)
                action.blockSignals(False)
                break
    
    @Slot()
    def toggle_game_from_tray(self):
        """从托盘菜单切换游戏监控状态"""
        action = self.sender()
        if action:
            game_name = action.data()
            enabled = action.isChecked()
            
            for game_config in self.monitor.game_configs:
                if game_config.name == game_name:
                    if game_config.enabled != enabled:
                        game_config.enabled = enabled
                        if enabled:
                            # 如果是从无启用游戏到有启用游戏，设置running为True
                            was_running = self.monitor.running
                            if not was_running:
                                self.monitor.running = True
                                logger.info("监控程序已启动")
                            
                            # 启用游戏监控
                            self.monitor.start_monitor_thread(game_config)
                        else:
                            # 停止该游戏的监控
                            self.monitor.stop_monitor_thread(game_config)
                            
                            # 检查是否还有其他启用的游戏
                            if not any(g.enabled for g in self.monitor.game_configs):
                                # 如果没有任何启用的游戏，重置监控器状态
                                logger.info("所有游戏监控已关闭")
                                self.monitor.running = False
                                self.monitor.anticheat_killed = False
                                self.monitor.scanprocess_optimized = False
                                logger.info("监控程序已停止")
                        
                        # 保存配置
                        self.monitor.config_manager.save_config()
                        
                        # 立即更新状态显示
                        self.update_status()
                    
                    # 更新主窗口游戏列表
                    for i in range(self.games_list.count()):
                        item = self.games_list.item(i)
                        widget = self.games_list.itemWidget(item)
                        if widget.game_name == game_name:
                            widget.set_checked(enabled)
                            break
                    break
    
    @Slot()
    def open_config_dir(self):
        """打开配置目录"""
        try:
            if os.path.exists(self.monitor.config_manager.config_dir):
                if sys.platform == 'win32':
                    os.startfile(self.monitor.config_manager.config_dir)
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', self.monitor.config_manager.config_dir])
                logger.info(f"已打开配置目录: {self.monitor.config_manager.config_dir}")
            else:
                os.makedirs(self.monitor.config_manager.config_dir, exist_ok=True)
                if sys.platform == 'win32':
                    os.startfile(self.monitor.config_manager.config_dir)
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', self.monitor.config_manager.config_dir])
                logger.info(f"已创建并打开配置目录: {self.monitor.config_manager.config_dir}")
        except Exception as e:
            logger.error(f"打开配置目录失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"打开配置目录失败: {str(e)}")
    
    @Slot()
    def check_update(self):
        """检查更新"""
        QMessageBox.information(self, "检查更新", "请前往 GitHub 项目页面获取最新版本。")
        # 可以调用系统浏览器打开项目地址
        import webbrowser
        webbrowser.open("https://github.com/cassianvale/ACE-KILLER/releases/latest")
    
    @Slot()
    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于 ACE-KILLER", 
                         "ACE-KILLER\n\n"
                         "版本: 1.0.2\n"
                         "作者: CassianVale\n\n"
                         "GitHub: https://github.com/cassianvale/ACE-KILLER\n\n"
                         "ACE-KILLER是一款游戏优化工具，用于监控并优化游戏进程")
    
    @Slot()
    def show_main_window(self):
        """显示主窗口"""
        self.showNormal()
        self.activateWindow()
    
    @Slot()
    def show_status(self):
        """在托盘菜单显示状态通知"""
        status = get_status_info(self.monitor)
        send_notification(
            title="ACE-KILLER 状态",
            message=status,
            icon_path=self.icon_path
        )
    
    @Slot()
    def tray_icon_activated(self, reason):
        """处理托盘图标激活事件"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_main_window()
    
    @Slot()
    def confirm_exit(self):
        """确认退出程序"""
        self.exit_app()
    
    def exit_app(self):
        """退出应用程序"""
        # 停止所有监控
        if self.monitor.running:
            self.monitor.running = False
        
        # 停止定时器
        self.update_timer.stop()
        
        # 移除托盘图标
        self.tray_icon.hide()
        
        # 退出应用
        QApplication.quit()
    
    def changeEvent(self, event):
        """处理窗口状态变化事件"""
        if event.type() == QEvent.WindowStateChange and self.isMinimized():
            # 窗口最小化时隐藏窗口
            self.hide()
            event.accept()
        else:
            super().changeEvent(event)
    
    def closeEvent(self, event):
        """直接退出程序"""
        event.accept()
        self.exit_app()


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
    
    # 检查进程状态
    if any_game_running:
        status_lines.append(f"🎮 游戏主程序：运行中 ({', '.join(running_games)})")
        
        # 检查 ACE-Tray.exe 是否存在
        ace_proc = monitor.is_process_running(monitor.anticheat_name)
        if not ace_proc and monitor.anticheat_killed:
            status_lines.append("✅ ACE进程：已终止")
        elif not ace_proc:
            status_lines.append("ℹ️ ACE进程：未运行")
        elif ace_proc and monitor.anticheat_killed:
            status_lines.append("⏳ ACE进程：处理中")
        else:
            status_lines.append("❗ ACE进程：需要处理")
        
        # 检查 SGuard64.exe 是否存在
        scan_proc = monitor.is_process_running(monitor.scanprocess_name)
        if not scan_proc and monitor.scanprocess_optimized:
            status_lines.append("✅ SGuard64进程：已优化")
        elif not scan_proc:
            status_lines.append("ℹ️ SGuard64进程：未运行")
        elif scan_proc and monitor.scanprocess_optimized:
            # 验证是否真的优化了
            try:
                is_running, is_optimized = monitor.check_process_status(monitor.scanprocess_name)
                if is_running and is_optimized:
                    status_lines.append("✅ SGuard64进程：已优化")
                else:
                    status_lines.append("⏳ SGuard64进程：优化中")
            except Exception:
                # 如果无法检查状态，显示处理中
                status_lines.append("⏳ SGuard64进程：优化中") 
        else:
            status_lines.append("❗ SGuard64进程：需要优化")
    else:
        status_lines.append("🎮 游戏主程序：未运行")
    
    status_lines.append("\n⚙️ 系统设置：")
    status_lines.append("  🔔 通知状态：" + ("开启" if monitor.show_notifications else "关闭"))
    status_lines.append(f"  🔁 开机自启：{'开启' if monitor.auto_start else '关闭'}")
    status_lines.append(f"  📁 配置目录：{monitor.config_manager.config_dir}")
    status_lines.append(f"  📝 日志目录：{monitor.config_manager.log_dir}")
    status_lines.append(f"  ⏱️ 日志保留：{monitor.config_manager.log_retention_days}天")
    
    return "\n".join(status_lines)


def create_gui(monitor, icon_path=None):
    """
    创建图形用户界面
    
    Args:
        monitor: 进程监控器对象
        icon_path: 图标路径
        
    Returns:
        (QApplication, MainWindow): 应用程序对象和主窗口对象
    """
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    window = MainWindow(monitor, icon_path)
    return app, window 