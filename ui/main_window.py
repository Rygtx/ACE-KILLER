#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
PySide6 GUI界面模块
"""

import os
import sys
import qdarktheme
import darkdetect
import threading
import subprocess
import time
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QCheckBox, QSystemTrayIcon, QMenu, 
    QListWidget, QListWidgetItem, QGroupBox, QTabWidget, QFrame,
    QMessageBox, QScrollArea, QStyle, QDialog, QLineEdit, QFormLayout,
    QGridLayout, QProgressDialog, QProgressBar, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize, QObject, Slot, QTimer, QEvent, QThread, QMetaObject, QGenericArgument
from PySide6.QtGui import QIcon, QPixmap, QColor, QAction
from loguru import logger

from utils.notification import send_notification
from core.system_utils import enable_auto_start, disable_auto_start
from utils.memory_cleaner import get_memory_cleaner
from utils.process_io_priority import get_io_priority_manager, IO_PRIORITY_HINT


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


class GameConfigDialog(QDialog):
    """游戏配置对话框"""
    
    def __init__(self, parent=None, game_config=None):
        super().__init__(parent)
        self.game_config = game_config
        self.is_edit_mode = game_config is not None
        
        self.setup_ui()
        
        if self.is_edit_mode:
            self.setWindowTitle("编辑游戏配置")
            self.name_edit.setText(game_config.name)
            self.launcher_edit.setText(game_config.launcher)
            self.main_game_edit.setText(game_config.main_game)
            # 编辑模式下不允许修改名称
            self.name_edit.setReadOnly(True)
        else:
            self.setWindowTitle("添加游戏配置")
    
    def setup_ui(self):
        """设置对话框UI"""
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # 游戏名称
        self.name_edit = QLineEdit()
        form_layout.addRow("游戏名称:", self.name_edit)
        
        # 启动器进程名
        self.launcher_edit = QLineEdit()
        form_layout.addRow("启动器进程名:", self.launcher_edit)
        
        # 游戏主进程名
        self.main_game_edit = QLineEdit()
        form_layout.addRow("游戏主进程名:", self.main_game_edit)
        
        layout.addLayout(form_layout)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 确定按钮
        self.ok_button = QPushButton("确定")
        self.ok_button.clicked.connect(self.accept)
        
        # 取消按钮
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setMinimumWidth(300)


class ProcessIoPriorityListDialog(QDialog):
    """I/O优先级进程列表管理对话框"""
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.setup_ui()
        self.load_processes()
    
    def setup_ui(self):
        """设置UI"""
        self.setWindowTitle("I/O优先级进程列表管理")
        self.setMinimumSize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # 提示标签
        info_label = QLabel(
            "以下进程会在程序启动和运行期间定期自动设置I/O优先级。\n"
            "这有助于减少这些进程的磁盘读写活动，提高系统响应速度。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 进程表格
        self.table = QTableWidget()
        self.table.setColumnCount(3)  # 进程名、优先级、操作
        self.table.setHorizontalHeaderLabels(["进程名", "优先级", "操作"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)
        
        # 按钮布局
        button_layout = QHBoxLayout()
        
        # 关闭按钮
        self.close_btn = QPushButton("关闭")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def load_processes(self):
        """加载进程列表"""
        self.table.setRowCount(0)
        
        if not self.config_manager or not hasattr(self.config_manager, 'io_priority_processes'):
            return
        
        # 设置行数
        self.table.setRowCount(len(self.config_manager.io_priority_processes))
        
        # 填充数据
        for row, process in enumerate(self.config_manager.io_priority_processes):
            # 进程名
            name_item = QTableWidgetItem(process.get('name', ''))
            self.table.setItem(row, 0, name_item)
            
            # 优先级
            priority = process.get('priority', 0)
            priority_text = self._get_priority_text(priority)
            priority_item = QTableWidgetItem(priority_text)
            self.table.setItem(row, 1, priority_item)
            
            # 删除按钮
            delete_btn = QPushButton("删除")
            delete_btn.setProperty("row", row)
            delete_btn.clicked.connect(self.delete_process)
            self.table.setCellWidget(row, 2, delete_btn)
    
    def _get_priority_text(self, priority):
        """获取优先级的文本表示"""
        if priority == 0:
            return "最低"
        elif priority == 1:
            return "低"
        elif priority == 2:
            return "正常"
        elif priority == 3:
            return "关键"
        else:
            return f"未知({priority})"
    
    def delete_process(self):
        """删除一个进程"""
        sender = self.sender()
        if not sender:
            return
        
        row = sender.property("row")
        if row is None or row < 0 or row >= len(self.config_manager.io_priority_processes):
            return
        
        process_name = self.config_manager.io_priority_processes[row].get('name', '')
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要从自动I/O优先级列表中删除进程 '{process_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 删除进程
        del self.config_manager.io_priority_processes[row]
        
        # 保存配置
        if self.config_manager.save_config():
            # 重新加载列表
            self.load_processes()
        else:
            QMessageBox.warning(self, "保存失败", "删除进程后保存配置失败")


class MainWindow(QMainWindow):
    """主窗口"""
    
    configChanged = Signal()
    
    # 添加进度更新信号作为类属性
    progress_update_signal = Signal(int)
    
    def __init__(self, monitor, icon_path=None):
        super().__init__()
        
        self.monitor = monitor
        self.icon_path = icon_path
        self.current_theme = "auto"  # 支持 "light", "dark", "auto"
        
        # 初始化内存清理管理器
        self.memory_cleaner = get_memory_cleaner()
        
        # 连接信号到槽函数
        self.progress_update_signal.connect(self._update_progress_dialog_value)
        
        self.setup_ui()
        self.setup_tray()
        
        # 添加定时器，定期更新状态
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_status)
        self.update_timer.start(1000)
        
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
        
        # 创建一个QLabel用于显示状态信息
        self.status_label = QLabel("加载中...")
        self.status_label.setWordWrap(True)
        self.status_label.setTextFormat(Qt.RichText)
        self.status_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.status_label.setContentsMargins(5, 5, 5, 5)
        
        # 创建滚动区域
        status_scroll = QScrollArea()
        status_scroll.setWidgetResizable(True)
        status_scroll.setWidget(self.status_label)
        status_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        status_scroll.setFrameShape(QFrame.NoFrame)
        
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
        self.games_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.games_list.customContextMenuRequested.connect(self.show_games_context_menu)
        games_box_layout.addWidget(self.games_list)
        games_group.setLayout(games_box_layout)
        games_layout.addWidget(games_group)
        
        # 添加I/O优先级设置功能到游戏监控选项卡
        io_priority_group = QGroupBox("进程I/O优先级")
        io_priority_layout = QVBoxLayout()
        
        # 添加说明标签
        io_priority_label = QLabel("降低进程的磁盘I/O优先级可以减少系统卡顿，提高前台应用的响应速度。"
            "特别适用于降低反作弊、杀毒等后台扫描程序的优先级。")
        io_priority_label.setWordWrap(True)
        io_priority_layout.addWidget(io_priority_label)
        
        # 进程选择和优先级设置区域
        process_layout = QHBoxLayout()
        
        # 进程选择下拉框
        self.process_combo = QComboBox()
        self.process_combo.addItem("SGuard64.exe", "SGuard64.exe")  # 存储进程名称作为userData
        self.process_combo.addItem("ACE-Tray.exe", "ACE-Tray.exe")
        self.process_combo.setEditable(True)  # 允许用户输入自定义进程名
        process_layout.addWidget(QLabel("目标进程:"))
        process_layout.addWidget(self.process_combo, 1)  # 1是stretch因子
        
        # 优先级选择下拉框
        self.priority_combo = QComboBox()
        self.priority_combo.addItem("很低 (推荐)", IO_PRIORITY_HINT.IoPriorityVeryLow)
        self.priority_combo.addItem("低", IO_PRIORITY_HINT.IoPriorityLow)
        self.priority_combo.addItem("正常", IO_PRIORITY_HINT.IoPriorityNormal)
        self.priority_combo.addItem("关键", IO_PRIORITY_HINT.IoPriorityCritical)
        process_layout.addWidget(QLabel("优先级:"))
        process_layout.addWidget(self.priority_combo)
        
        io_priority_layout.addLayout(process_layout)
        
        # 应用按钮
        self.apply_io_priority_btn = QPushButton("应用I/O优先级设置")
        self.apply_io_priority_btn.clicked.connect(self.apply_io_priority)
        io_priority_layout.addWidget(self.apply_io_priority_btn)
        
        # 常用预设按钮布局
        preset_layout = QHBoxLayout()
        
        # 预设：优化所有反作弊进程
        self.optimize_anticheat_btn = QPushButton("一键优化所有反作弊进程")
        self.optimize_anticheat_btn.clicked.connect(self.optimize_anticheat_processes)
        preset_layout.addWidget(self.optimize_anticheat_btn)
        
        # 预设：优化当前游戏相关进程
        self.optimize_current_game_btn = QPushButton("优化当前游戏体验")
        self.optimize_current_game_btn.clicked.connect(self.optimize_current_game)
        preset_layout.addWidget(self.optimize_current_game_btn)
        
        # 管理自动设置列表按钮
        self.manage_io_list_btn = QPushButton("管理自动优化列表")
        self.manage_io_list_btn.clicked.connect(self.show_io_priority_list)
        preset_layout.addWidget(self.manage_io_list_btn)
        
        io_priority_layout.addLayout(preset_layout)
        
        # 提示标签
        note_label = QLabel("注意: 优先级设置在进程重启后会恢复默认值，建议设置开机自启动")
        note_label.setStyleSheet("color: #888888; font-style: italic;")
        io_priority_layout.addWidget(note_label)
        
        io_priority_group.setLayout(io_priority_layout)
        games_layout.addWidget(io_priority_group)
        
        # 增加提示性文本
        games_tip_label = QLabel("提示：右键游戏列表可自定义添加、编辑或删除游戏配置")
        games_tip_label.setStyleSheet("color: #888888; font-size: 13px;")
        games_tip_label.setWordWrap(True)
        games_layout.addWidget(games_tip_label)
        
        # 内存清理选项卡
        memory_tab = QWidget()
        memory_layout = QVBoxLayout(memory_tab)
        
        # 自动清理选项
        auto_group = QGroupBox("自动清理")
        auto_layout = QVBoxLayout()
        
        # 定时选项
        self.clean_option1 = QCheckBox("每过5分钟，截取进程工作集")
        self.clean_option1.stateChanged.connect(lambda state: self.toggle_clean_option(0, state))
        auto_layout.addWidget(self.clean_option1)
        
        self.clean_option2 = QCheckBox("每过5分钟，清理系统缓存")
        self.clean_option2.stateChanged.connect(lambda state: self.toggle_clean_option(1, state))
        auto_layout.addWidget(self.clean_option2)
        
        self.clean_option3 = QCheckBox("每过5分钟，用全部可能的方法清理内存")
        self.clean_option3.stateChanged.connect(lambda state: self.toggle_clean_option(2, state))
        auto_layout.addWidget(self.clean_option3)
        
        auto_layout.addSpacing(10)
        
        # 使用比例超出80%的选项
        self.clean_option4 = QCheckBox("若内存使用量超出80%，截取进程工作集")
        self.clean_option4.stateChanged.connect(lambda state: self.toggle_clean_option(3, state))
        auto_layout.addWidget(self.clean_option4)
        
        self.clean_option5 = QCheckBox("若内存使用量超出80%，清理系统缓存")
        self.clean_option5.stateChanged.connect(lambda state: self.toggle_clean_option(4, state))
        auto_layout.addWidget(self.clean_option5)
        
        self.clean_option6 = QCheckBox("若内存使用量超出80%，用全部可能的方法清理内存")
        self.clean_option6.stateChanged.connect(lambda state: self.toggle_clean_option(5, state))
        auto_layout.addWidget(self.clean_option6)
        
        auto_group.setLayout(auto_layout)
        memory_layout.addWidget(auto_group)
        
        # 其他选项
        options_group = QGroupBox("选项")
        options_layout = QHBoxLayout()

        # 启用内存清理
        self.memory_checkbox = QCheckBox("启用内存清理")
        self.memory_checkbox.stateChanged.connect(self.toggle_memory_cleanup)
        options_layout.addWidget(self.memory_checkbox)
        
        # 暴力模式
        self.brute_mode_checkbox = QCheckBox("深度清理模式(调用Windows系统API)")
        self.brute_mode_checkbox.stateChanged.connect(self.toggle_brute_mode)
        self.brute_mode_checkbox.setToolTip("深度清理模式会使用Windows系统API清理所有进程的工作集，效率更高但更激进；\n"
                                           "不开启则会逐个进程分别清理工作集，相对温和但效率较低。")
        options_layout.addWidget(self.brute_mode_checkbox)
        
        options_group.setLayout(options_layout)
        memory_layout.addWidget(options_group)
        
        # 手动清理按钮
        buttons_group = QGroupBox("手动清理")
        buttons_layout = QVBoxLayout()
        
        # 按钮水平布局
        btn_row_layout = QHBoxLayout()
        
        # 截取进程工作集按钮
        self.clean_workingset_btn = QPushButton("截取进程工作集")
        self.clean_workingset_btn.clicked.connect(self.manual_clean_workingset)
        btn_row_layout.addWidget(self.clean_workingset_btn)
        
        # 清理系统缓存按钮
        self.clean_syscache_btn = QPushButton("清理系统缓存")
        self.clean_syscache_btn.clicked.connect(self.manual_clean_syscache)
        btn_row_layout.addWidget(self.clean_syscache_btn)
        
        # 全面清理按钮
        self.clean_all_btn = QPushButton("执行全部已知清理")
        self.clean_all_btn.clicked.connect(self.manual_clean_all)
        btn_row_layout.addWidget(self.clean_all_btn)
        
        buttons_layout.addLayout(btn_row_layout)
        
        # 添加提示文本
        warning_label = QLabel("如果已经开启游戏不建议点击全部已知清理，否则清理时可能导致现有游戏卡死，或者清理后一段时间内游戏变卡")
        warning_label.setStyleSheet("color: red;")
        warning_label.setWordWrap(True)
        buttons_layout.addWidget(warning_label)
        
        buttons_group.setLayout(buttons_layout)
        memory_layout.addWidget(buttons_group)
        
        # 添加状态显示
        memory_status = QGroupBox("内存状态")
        memory_status_layout = QVBoxLayout()
        
        # 创建内存信息标签
        self.memory_info_label = QLabel("加载中...")
        self.memory_info_label.setAlignment(Qt.AlignCenter)
        memory_status_layout.addWidget(self.memory_info_label)
        
        # 创建内存使用进度条
        self.memory_progress = QProgressBar()
        self.memory_progress.setMinimum(0)
        self.memory_progress.setMaximum(100)
        self.memory_progress.setValue(0)
        memory_status_layout.addWidget(self.memory_progress)
        
        # 创建清理统计信息标签
        self.clean_stats_label = QLabel("清理统计: 暂无数据")
        self.clean_stats_label.setAlignment(Qt.AlignCenter)
        memory_status_layout.addWidget(self.clean_stats_label)
        
        memory_status.setLayout(memory_status_layout)
        memory_layout.addWidget(memory_status)
        
        # 填充剩余空间
        memory_layout.addStretch()
        
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
        
        # 日志设置
        log_group = QGroupBox("日志设置")
        log_layout = QVBoxLayout()
        self.debug_checkbox = QCheckBox("启用调试模式")
        self.debug_checkbox.stateChanged.connect(self.toggle_debug_mode)
        log_layout.addWidget(self.debug_checkbox)
        log_group.setLayout(log_layout)
        settings_layout.addWidget(log_group)
        
        # 主题设置
        theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout()
        
        # 主题选择水平布局
        theme_buttons_layout = QHBoxLayout()
        
        # 浅色主题按钮
        self.light_theme_btn = QPushButton("浅色")
        self.light_theme_btn.clicked.connect(lambda: self.switch_theme("light"))
        theme_buttons_layout.addWidget(self.light_theme_btn)
        
        # 跟随系统按钮
        self.auto_theme_btn = QPushButton("跟随系统")
        self.auto_theme_btn.clicked.connect(lambda: self.switch_theme("auto"))
        theme_buttons_layout.addWidget(self.auto_theme_btn)
        
        # 深色主题按钮
        self.dark_theme_btn = QPushButton("深色")
        self.dark_theme_btn.clicked.connect(lambda: self.switch_theme("dark"))
        theme_buttons_layout.addWidget(self.dark_theme_btn)
        
        theme_layout.addLayout(theme_buttons_layout)
        theme_group.setLayout(theme_layout)
        settings_layout.addWidget(theme_group)
        
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
        
        # 添加ACE服务管理功能
        service_group = QGroupBox("ACE服务管理")
        service_layout = QVBoxLayout()
        
        # 提醒文本
        warning_label = QLabel("警告：以下操作需要管理员权限，并会永久删除ACE反作弊服务")
        warning_label.setStyleSheet("color: red;")
        service_layout.addWidget(warning_label)
        
        # 删除ACE服务按钮
        self.delete_service_btn = QPushButton("删除ACE服务")
        self.delete_service_btn.setToolTip("删除ACE-GAME、ACE-BASE、AntiCheatExpert Service、AntiCheatExpert Protection服务")
        self.delete_service_btn.clicked.connect(self.delete_ace_services)
        service_layout.addWidget(self.delete_service_btn)
        
        service_group.setLayout(service_layout)
        settings_layout.addWidget(service_group)
        
        # 添加空白占位
        settings_layout.addStretch()
        
        # 添加选项卡
        tabs.addTab(status_tab, "  程序状态  ")
        tabs.addTab(games_tab, "  游戏监控  ")
        tabs.addTab(memory_tab, "  内存清理  ")
        tabs.addTab(settings_tab, "  设置  ")
    
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
        
        # 主题切换子菜单
        theme_menu = QMenu("主题设置")
        
        # 浅色主题动作
        light_theme_action = QAction("浅色", self)
        light_theme_action.triggered.connect(lambda: self.switch_theme("light"))
        theme_menu.addAction(light_theme_action)
        
        # 跟随系统动作
        auto_theme_action = QAction("跟随系统", self)
        auto_theme_action.triggered.connect(lambda: self.switch_theme("auto"))
        theme_menu.addAction(auto_theme_action)
        
        # 深色主题动作
        dark_theme_action = QAction("深色", self)
        dark_theme_action.triggered.connect(lambda: self.switch_theme("dark"))
        theme_menu.addAction(dark_theme_action)
        
        tray_menu.addMenu(theme_menu)
        
        tray_menu.addSeparator()
        
        # 游戏监控子菜单
        self.games_menu = QMenu("游戏监控")
        self.update_games_menu()  # 初始添加游戏菜单项
        tray_menu.addMenu(self.games_menu)
        
        tray_menu.addSeparator()
        
        # 删除ACE服务菜单项
        delete_service_action = QAction("删除ACE服务", self)
        delete_service_action.triggered.connect(self.delete_ace_services)
        tray_menu.addAction(delete_service_action)
        
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
    
    @Slot(str)
    def switch_theme(self, theme):
        """
        切换应用程序主题
        
        Args:
            theme: 主题类型，可以是 "light"、"dark" 或 "auto"
        """
        if theme != self.current_theme:
            self.current_theme = theme
            
            if theme == "auto":
                # 使用系统主题
                detected_theme = "dark" if darkdetect.isDark() else "light"
                qdarktheme.setup_theme(detected_theme)
                logger.debug(f"主题已设置为跟随系统 (当前检测到: {detected_theme})")
            else:
                # 使用指定主题
                qdarktheme.setup_theme(theme)
                logger.debug(f"主题已设置为: {theme}")
            
            # 立即更新状态显示
            self.update_status()
    
    def get_status_html(self):
        """获取HTML格式的状态信息"""
        if not self.monitor:
            return "<p>程序未启动</p>"
        
        # 创建HTML样式
        style = """
        <style>
            .card {
                margin: 10px 0;
                padding: 10px;
                border-radius: 8px;
                background-color: transparent; 
            }
            .section-title {
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 8px;
                color: #3498db;
            }
            .status-success {
                color: #4cd964;
                font-weight: bold;
            }
            .status-warning {
                color: #ffcc00;
                font-weight: bold;
            }
            .status-error {
                color: #ff3b30;
                font-weight: bold;
            }
            .status-normal {
                font-weight: bold;
            }
            .status-disabled {
                color: #8e8e93;
                font-weight: bold;
            }
            .status-item {
                margin: 4px 0;
            }
            .memory-bar {
                height: 10px;
                background-color: rgba(200, 200, 200, 0.2);
                border-radius: 5px;
                margin: 5px 0;
                position: relative;
                overflow: hidden;
            }
            .memory-bar-fill {
                height: 100%;
                background-color: #3498db;
                border-radius: 5px;
                transition: width 0.5s ease;
            }
            .update-time {
                font-size: 12px;
                color: #8e8e93;
                text-align: right;
                margin-top: 10px;
            }
        </style>
        """
        
        html = [style]
        
        # 主状态卡片
        html.append('<div class="card">')
        html.append('<div class="section-title">程序状态</div>')
        
        # 监控程序状态
        if self.monitor.running:
            html.append('<p class="status-item"><span class="status-success">🟩 监控程序运行中</span></p>')
        else:
            html.append('<p class="status-item"><span class="status-error">🟥 监控程序已停止</span></p>')
        
        # 检查是否有任何游戏在运行
        running_games = []
        for game_config in self.monitor.game_configs:
            if game_config.enabled and game_config.main_game_running:
                running_games.append(game_config.name)
        
        if running_games:
            html.append(f'<p class="status-item">🎮 游戏运行中: <span class="status-success">{", ".join(running_games)}</span></p>')
        else:
            html.append('<p class="status-item">🎮 <span class="status-disabled">无游戏运行中</span></p>')
        
        html.append('</div>')
        
        # 进程状态卡片
        html.append('<div class="card">')
        html.append('<div class="section-title">进程状态</div>')
        
        # ACE进程状态(ACE反作弊程序是否安装提示弹窗)
        ace_running = self.monitor.is_process_running(self.monitor.anticheat_name) is not None
        if ace_running and self.monitor.anticheat_killed:
            html.append('<p class="status-item">✅ ACE-Tray进程: <span class="status-success">已被优化</span></p>')
        elif ace_running:
            html.append('<p class="status-item">🔄 ACE-Tray进程: <span class="status-warning">正在运行</span></p>')
        else:
            html.append('<p class="status-item">⚠️ ACE-Tray进程: <span class="status-error">未在运行</span>  (ACE反作弊程序是否安装提示弹窗)</p>')
        
        # SGuard64进程状态
        scan_running = self.monitor.is_process_running(self.monitor.scanprocess_name) is not None
        if scan_running and self.monitor.scanprocess_optimized:
            html.append('<p class="status-item">✅ SGuard64进程: <span class="status-success">已被优化</span></p>')
        elif scan_running:
            html.append('<p class="status-item">🔄 SGuard64进程: <span class="status-warning">正在运行 (未优化)</span></p>')
        else:
            html.append('<p class="status-item">⚠️ SGuard64进程: <span class="status-error">未在运行</span>  (SGuard64反作弊扫盘进程)</p>')
        
        # AntiCheatExpert Service服务状态
        service_exists, status, start_type = self.monitor.check_service_status(self.monitor.anticheat_service_name)
        if service_exists:
            if status == 'running':
                html.append('<p class="status-item">✅ AntiCheatExpert服务: <span class="status-success">正在运行</span></p>')
            elif status == 'stopped':
                html.append('<p class="status-item">⚠️ AntiCheatExpert服务: <span class="status-error">已停止</span></p>')
            else:
                html.append(f'<p class="status-item">ℹ️ AntiCheatExpert服务: <span class="status-normal">{status}</span></p>')
            
            # 服务启动类型
            if start_type == 'auto':
                html.append('<p class="status-item">⚙️ AntiCheatExpert启动类型: <span class="status-success">自动启动</span></p>')
            elif start_type == 'disabled':
                html.append('<p class="status-item">⚙️ AntiCheatExpert启动类型: <span class="status-error">已禁用</span></p>')
            elif start_type == 'manual':
                html.append('<p class="status-item">⚙️ AntiCheatExpert启动类型: <span class="status-normal">手动</span></p>')
            else:
                html.append(f'<p class="status-item">⚙️ AntiCheatExpert启动类型: <span class="status-normal">{start_type}</span></p>')
        else:
            html.append('<p class="status-item">❓ AntiCheatExpert服务: <span class="status-disabled">未找到</span></p>')
        
        html.append('</div>')
        
        # 内存状态卡片
        html.append('<div class="card">')
        html.append('<div class="section-title">内存状态</div>')
        
        if self.memory_cleaner.running:
            mem_info = self.memory_cleaner.get_memory_info()
            if mem_info:
                used_percent = mem_info['percent']
                used_gb = mem_info['used'] / (1024**3)
                total_gb = mem_info['total'] / (1024**3)
                
                # 根据内存使用率设置颜色
                bar_color = "#2ecc71"  # 绿色（低）
                status_class = "status-success"
                if used_percent >= 80:
                    bar_color = "#e74c3c"  # 红色（高）
                    status_class = "status-error" 
                elif used_percent >= 60:
                    bar_color = "#f39c12"  # 橙色（中）
                    status_class = "status-warning"
                
                html.append(f'<p class="status-item">🛡️ 内存清理: <span class="status-success">已启用</span></p>')
                html.append(f'<p class="status-item">🍋‍🟩 内存使用: <span class="{status_class}">{used_percent:.1f}%</span> ({used_gb:.1f}GB / {total_gb:.1f}GB)</p>')
                
                # 内存使用进度条
                html.append('<div class="memory-bar">')
                html.append(f'<div class="memory-bar-fill" style="width: {used_percent}%; background-color: {bar_color};"></div>')
                html.append('</div>')
                
                # 系统缓存信息
                cache_info = self.memory_cleaner.get_system_cache_info()
                if cache_info:
                    cache_size = cache_info['current_size'] / (1024**3)
                    peak_size = cache_info['peak_size'] / (1024**3)
                    html.append(f'<p class="status-item">💾 系统缓存: <span class="status-normal">{cache_size:.1f}GB</span> (峰值: {peak_size:.1f}GB)</p>')
            else:
                html.append('<p class="status-item">🧠 内存清理: <span class="status-success">已启用</span></p>')
                html.append('<p class="status-item">无法获取内存信息</p>')
        else:
            html.append('<p class="status-item">🧠 内存清理: <span class="status-disabled">已禁用</span></p>')
        
        html.append('</div>')
        
        # 系统设置卡片
        html.append('<div class="card">')
        html.append('<div class="section-title">系统设置</div>')
        
        # 通知状态
        notification_class = "status-success" if self.monitor.show_notifications else "status-disabled"
        notification_text = "已启用" if self.monitor.show_notifications else "已禁用"
        html.append(f'<p class="status-item">🔔 通知功能: <span class="{notification_class}" style="font-weight: bold;">{notification_text}</span></p>')
        
        # 自启动状态
        autostart_class = "status-success" if self.monitor.auto_start else "status-disabled"
        autostart_text = "已启用" if self.monitor.auto_start else "已禁用"
        html.append(f'<p class="status-item">🔁 开机自启: <span class="{autostart_class}" style="font-weight: bold;">{autostart_text}</span></p>')
        
        # 调试模式状态
        debug_class = "status-warning" if self.monitor.config_manager.debug_mode else "status-disabled"
        debug_text = "已启用" if self.monitor.config_manager.debug_mode else "已禁用"
        html.append(f'<p class="status-item">🐛 调试模式: <span class="{debug_class}" style="font-weight: bold;">{debug_text}</span></p>')
        
        # 主题状态
        html.append(f'<p class="status-item">🎨 当前主题: <span class="status-normal">{self._get_theme_display_name()}</span></p>')
        
        html.append('</div>')
        
        # 添加更新时间
        import datetime
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html.append(f'<p class="update-time">更新时间: {current_time}</p>')
        
        return "".join(html)
    
    def _get_theme_display_name(self):
        """获取主题的显示名称"""
        if self.current_theme == "light":
            return "浅色"
        elif self.current_theme == "dark":
            return "深色"
        else:  # auto
            return "跟随系统"
    
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
        
        # 更新调试模式设置
        self.debug_checkbox.setChecked(self.monitor.config_manager.debug_mode)
        
        # 加载内存清理设置
        # 使用配置中的enabled属性设置复选框状态
        self.memory_checkbox.setChecked(self.memory_cleaner.enabled)
        
        # 如果enabled为true但未运行，则启动内存清理线程
        if self.memory_cleaner.enabled and not self.memory_cleaner.running:
            self.memory_cleaner.start_cleaner_thread()
        
        # 加载暴力模式设置
        self.brute_mode_checkbox.setChecked(self.memory_cleaner.brute_mode)
        
        # 加载清理选项设置
        self.clean_option1.setChecked(self.memory_cleaner.clean_switches[0])
        self.clean_option2.setChecked(self.memory_cleaner.clean_switches[1])
        self.clean_option3.setChecked(self.memory_cleaner.clean_switches[2])
        self.clean_option4.setChecked(self.memory_cleaner.clean_switches[3])
        self.clean_option5.setChecked(self.memory_cleaner.clean_switches[4])
        self.clean_option6.setChecked(self.memory_cleaner.clean_switches[5])
        
        self.update_status()
        self.blockSignals(False)
    
    def update_status(self):
        """更新状态信息"""
        if not self.monitor:
            self.status_label.setText("<p>程序未启动</p>")
            return
            
        # 获取状态HTML
        status_html = self.get_status_html()
        
        # 设置状态文本
        self.status_label.setText(status_html)
        
        # 更新内存信息显示
        self.update_memory_status()
        
        # 更新托盘图标提示
        if self.tray_icon:
            mem_info = self.memory_cleaner.get_memory_info() if self.memory_cleaner.running else None
            mem_usage = f" - 内存: {mem_info['percent']:.1f}%" if mem_info else ""
            self.tray_icon.setToolTip(f"ACE-KILLER - {'运行中' if self.monitor.running else '已停止'}{mem_usage}")
        
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
    
    def update_memory_status(self):
        """更新内存状态显示"""
        # 更新内存信息
        mem_info = self.memory_cleaner.get_memory_info()
        if not mem_info:
            self.memory_info_label.setText("无法获取内存信息")
            self.memory_progress.setValue(0)
            return
            
        used_percent = mem_info['percent']
        used_gb = mem_info['used'] / (1024**3)
        total_gb = mem_info['total'] / (1024**3)
        
        # 更新标签文本
        self.memory_info_label.setText(f"物理内存: {used_gb:.1f}GB / {total_gb:.1f}GB ({used_percent:.1f}%)")
        
        # 更新进度条
        self.memory_progress.setValue(int(used_percent))
        
        # 根据内存使用率设置进度条颜色
        if used_percent >= 80:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: #e74c3c; }")
        elif used_percent >= 60:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: #f39c12; }")
        else:
            self.memory_progress.setStyleSheet("QProgressBar::chunk { background-color: #2ecc71; }")
            
        # 更新清理统计信息
        stats = self.memory_cleaner.get_clean_stats()
        stats_text = (f"累计释放: {stats['total_cleaned_mb']:.2f}MB | "
                     f"上次释放: {stats['last_cleaned_mb']:.2f}MB | "
                     f"清理次数: {stats['clean_count']} | "
                     f"最后清理: {stats['last_clean_time']}")
        self.clean_stats_label.setText(stats_text)
    
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
            logger.debug(f"通知状态已更改并保存: {'开启' if self.monitor.config_manager.show_notifications else '关闭'}")
        else:
            logger.warning(f"通知状态已更改但保存失败: {'开启' if self.monitor.config_manager.show_notifications else '关闭'}")
        
        # 立即更新状态显示
        self.update_status()
    
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
            logger.debug(f"通知状态已更改并保存: {'开启' if self.monitor.config_manager.show_notifications else '关闭'}")
        else:
            logger.warning(f"通知状态已更改但保存失败: {'开启' if self.monitor.config_manager.show_notifications else '关闭'}")
        
        # 立即更新状态显示
        self.update_status()
    
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
            logger.debug(f"开机自启状态已更改并保存: {'开启' if self.monitor.config_manager.auto_start else '关闭'}")
        else:
            logger.warning(f"开机自启状态已更改但保存失败: {'开启' if self.monitor.config_manager.auto_start else '关闭'}")
        
        # 立即更新状态显示
        self.update_status()
    
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
            logger.debug(f"开机自启状态已更改并保存: {'开启' if self.monitor.config_manager.auto_start else '关闭'}")
        else:
            logger.warning(f"开机自启状态已更改但保存失败: {'开启' if self.monitor.config_manager.auto_start else '关闭'}")
        
        # 立即更新状态显示
        self.update_status()
    
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
                            logger.debug("监控程序已启动")
                        
                        # 启用游戏监控
                        self.monitor.start_monitor_thread(game_config)
                    else:
                        # 停止该游戏的监控
                        self.monitor.stop_monitor_thread(game_config)
                        
                        # 检查是否还有其他启用的游戏
                        if not any(g.enabled for g in self.monitor.game_configs):
                            # 如果没有任何启用的游戏，重置监控器状态
                            logger.debug("所有游戏监控已关闭")
                            self.monitor.running = False
                            self.monitor.anticheat_killed = False
                            self.monitor.scanprocess_optimized = False
                            logger.debug("监控程序已停止")
                    
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
                                logger.debug("监控程序已启动")
                            
                            # 启用游戏监控
                            self.monitor.start_monitor_thread(game_config)
                        else:
                            # 停止该游戏的监控
                            self.monitor.stop_monitor_thread(game_config)
                            
                            # 检查是否还有其他启用的游戏
                            if not any(g.enabled for g in self.monitor.game_configs):
                                # 如果没有任何启用的游戏，重置监控器状态
                                logger.debug("所有游戏监控已关闭")
                                self.monitor.running = False
                                self.monitor.anticheat_killed = False
                                self.monitor.scanprocess_optimized = False
                                logger.debug("监控程序已停止")
                        
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
                logger.debug(f"已打开配置目录: {self.monitor.config_manager.config_dir}")
            else:
                os.makedirs(self.monitor.config_manager.config_dir, exist_ok=True)
                if sys.platform == 'win32':
                    os.startfile(self.monitor.config_manager.config_dir)
                else:
                    import subprocess
                    subprocess.Popen(['xdg-open', self.monitor.config_manager.config_dir])
                logger.debug(f"已创建并打开配置目录: {self.monitor.config_manager.config_dir}")
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
                         "版本: 1.0.3\n"
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
        
        # 确保在主线程中停止定时器
        if QThread.currentThread() == QApplication.instance().thread():
            # 当前在主线程
            self.update_timer.stop()
        else:
            # 当前不在主线程，使用QMetaObject.invokeMethod
            QMetaObject.invokeMethod(self.update_timer, "stop", 
                                   Qt.ConnectionType.QueuedConnection)
        
        # 移除托盘图标
        if QThread.currentThread() == QApplication.instance().thread():
            self.tray_icon.hide()
        else:
            QMetaObject.invokeMethod(self.tray_icon, "hide",
                                   Qt.ConnectionType.QueuedConnection)
        
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

    @Slot(object)
    def show_games_context_menu(self, pos):
        """显示游戏列表右键菜单"""
        context_menu = QMenu(self)
        
        # 添加游戏配置
        add_action = QAction("添加游戏配置", self)
        add_action.triggered.connect(self.add_game_config)
        context_menu.addAction(add_action)
        
        # 获取当前选中项
        current_item = self.games_list.itemAt(pos)
        
        if current_item:
            # 编辑菜单项
            edit_action = QAction("编辑游戏配置", self)
            edit_action.triggered.connect(lambda: self.edit_game_config(current_item))
            context_menu.addAction(edit_action)
            
            # 删除菜单项
            delete_action = QAction("删除游戏配置", self)
            delete_action.triggered.connect(lambda: self.delete_game_config(current_item))
            context_menu.addAction(delete_action)
        
        context_menu.exec(self.games_list.mapToGlobal(pos))
    
    @Slot()
    def add_game_config(self):
        """添加游戏配置"""
        dialog = GameConfigDialog(self)
        if dialog.exec():
            name = dialog.name_edit.text().strip()
            launcher = dialog.launcher_edit.text().strip()
            main_game = dialog.main_game_edit.text().strip()
            
            # 验证输入
            if not name or not launcher or not main_game:
                QMessageBox.warning(self, "输入错误", "请填写所有字段")
                return
            
            # 检查名称是否已存在
            if any(config.name == name for config in self.monitor.game_configs):
                QMessageBox.warning(self, "输入错误", f"游戏配置 '{name}' 已存在")
                return
            
            # 添加游戏配置
            self.monitor.config_manager.add_game_config(name, launcher, main_game, True)
            
            # 更新游戏列表和菜单
            self.update_games_menu()
            
            logger.debug(f"已添加游戏配置: {name}")
    
    @Slot(QListWidgetItem)
    def edit_game_config(self, list_item):
        """编辑游戏配置"""
        # 获取游戏名称
        widget = self.games_list.itemWidget(list_item)
        if not widget:
            return
        
        game_name = widget.game_name
        
        # 获取游戏配置
        game_config = self.monitor.config_manager.get_game_config(game_name)
        if not game_config:
            return
        
        dialog = GameConfigDialog(self, game_config)
        if dialog.exec():
            launcher = dialog.launcher_edit.text().strip()
            main_game = dialog.main_game_edit.text().strip()
            
            # 验证输入
            if not launcher or not main_game:
                QMessageBox.warning(self, "输入错误", "请填写所有字段")
                return
            
            # 更新配置
            game_config.launcher = launcher
            game_config.main_game = main_game
            
            # 保存配置
            self.monitor.config_manager.save_config()
            
            logger.debug(f"已更新游戏配置: {game_name}")
    
    @Slot(QListWidgetItem)
    def delete_game_config(self, list_item):
        """删除游戏配置"""
        # 获取游戏名称
        widget = self.games_list.itemWidget(list_item)
        if not widget:
            return
        
        game_name = widget.game_name
        
        # 确认删除
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除游戏配置 '{game_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 查找游戏配置
            game_config = None
            for config in self.monitor.game_configs:
                if config.name == game_name:
                    game_config = config
                    break
            
            if game_config:
                # 如果游戏正在监控中，先停止监控
                if game_config.enabled:
                    # 先将enabled设置为False以便线程退出循环
                    game_config.enabled = False
                    # 停止监控线程
                    self.monitor.stop_monitor_thread(game_config)
                    logger.debug(f"已停止游戏 '{game_name}' 的监控线程")
                    
                    # 检查是否还有其他启用的游戏
                    if not any(g.enabled for g in self.monitor.game_configs if g.name != game_name):
                        # 如果没有其他启用的游戏，重置监控器状态
                        logger.debug("所有游戏监控已关闭")
                        self.monitor.running = False
                        self.monitor.anticheat_killed = False
                        self.monitor.scanprocess_optimized = False
                        logger.debug("监控程序已停止")
            
            # 删除游戏配置
            self.monitor.config_manager.remove_game_config(game_name)
            
            # 更新游戏列表和菜单
            self.update_games_menu()
            
            # 更新状态显示
            self.update_status()
            
            logger.debug(f"已删除游戏配置: {game_name}")

    @Slot()
    def toggle_debug_mode(self):
        """切换调试模式"""
        # 获取新的调试模式状态
        new_debug_mode = self.debug_checkbox.isChecked()
        self.monitor.config_manager.debug_mode = new_debug_mode
        
        # 保存配置
        if self.monitor.config_manager.save_config():
            logger.debug(f"调试模式已更改并保存: {'开启' if new_debug_mode else '关闭'}")
        else:
            logger.warning(f"调试模式已更改但保存失败: {'开启' if new_debug_mode else '关闭'}")
        
        # 重新初始化日志系统
        from utils.logger import setup_logger
        setup_logger(
            self.monitor.config_manager.log_dir,
            self.monitor.config_manager.log_retention_days,
            self.monitor.config_manager.log_rotation,
            new_debug_mode
        )
        
        # 立即更新状态显示
        self.update_status()

    @Slot()
    def toggle_memory_cleanup(self):
        """切换内存清理功能开关"""
        enabled = self.memory_checkbox.isChecked()
        
        # 更新内存清理器的enabled属性
        self.memory_cleaner.enabled = enabled
        
        if enabled and not self.memory_cleaner.running:
            # 启动内存清理线程
            self.memory_cleaner.start_cleaner_thread()
            logger.debug("内存清理功能已启用")
        elif not enabled and self.memory_cleaner.running:
            # 停止内存清理线程 - 非阻塞方式
            self.memory_cleaner.stop_cleaner_thread()
            logger.debug("内存清理功能正在停止")
        
        # 将设置同步到配置管理器
        self.memory_cleaner.sync_to_config_manager()
        
        # 立即更新UI状态，而不等待线程完全停止
        self.update_memory_status()
    
    @Slot()
    def toggle_brute_mode(self):
        """切换暴力模式开关"""
        enabled = self.brute_mode_checkbox.isChecked()
        
        # 更新配置
        self.memory_cleaner.brute_mode = enabled
        
        # 将设置同步到配置管理器
        self.memory_cleaner.sync_to_config_manager()
        
        logger.debug(f"内存清理暴力模式已{'启用' if enabled else '禁用'}")
    
    @Slot(int, int)
    def toggle_clean_option(self, option_index, state):
        """切换清理选项"""
        # PySide6中Qt.Checked的值为2
        enabled = (state == 2)
        
        self.memory_cleaner.clean_switches[option_index] = enabled
        
        # 将设置同步到配置管理器
        self.memory_cleaner.sync_to_config_manager()
        
        # 将索引转换为实际的选项编号
        option_number = option_index + 1
        logger.debug(f"内存清理选项 {option_number} 已{'启用' if enabled else '禁用'}")
    
    @Slot()
    def _update_progress_dialog_value(self, value):
        """更新进度对话框的值（从主线程）"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog is not None:
            self.progress_dialog.setValue(value)
    
    @Slot()
    def manual_clean_workingset(self):
        """手动清理工作集"""
        try:
            cleaned_mb = self.memory_cleaner.trim_process_working_set()
            self.update_memory_status()
            logger.debug(f"手动清理工作集完成，释放了 {cleaned_mb:.2f}MB 内存")
        except Exception as e:
            logger.error(f"手动清理工作集失败: {str(e)}")
    
    @Slot()
    def manual_clean_syscache(self):
        """手动清理系统缓存"""
        try:
            cleaned_mb = self.memory_cleaner.flush_system_buffer()
            self.update_memory_status()
            logger.debug(f"手动清理系统缓存完成，释放了 {cleaned_mb:.2f}MB 内存")
        except Exception as e:
            logger.error(f"手动清理系统缓存失败: {str(e)}")
    
    @Slot()
    def manual_clean_all(self):
        """手动执行全面清理"""
        # 添加二次确认对话框
        reply = QMessageBox.question(
            self,
            "清理确认",
            "如果已经开启游戏不建议点击全部已知清理，否则清理时可能导致现有游戏卡死，或者清理后一段时间内游戏变卡\n\n确定要继续执行全部清理吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 显示进度对话框
        self.progress_dialog = QProgressDialog("正在清理内存...", "取消", 0, 3, self)
        self.progress_dialog.setWindowTitle("全面内存清理")
        self.progress_dialog.setModal(True)
        self.progress_dialog.setMinimumDuration(0)
        self.progress_dialog.setValue(0)
        
        # 创建一个线程来执行清理
        def clean_thread_func():
            try:
                total_cleaned = 0
                
                # 清理工作集
                cleaned_mb = self.memory_cleaner.trim_process_working_set()
                total_cleaned += cleaned_mb
                # 通过信号更新UI，而不是直接修改
                self.progress_update_signal.emit(1)
                
                # 清理系统缓存
                cleaned_mb = self.memory_cleaner.flush_system_buffer()
                total_cleaned += cleaned_mb
                self.progress_update_signal.emit(2)
                
                # 全面清理
                cleaned_mb = self.memory_cleaner.clean_memory_all()
                total_cleaned += cleaned_mb
                self.progress_update_signal.emit(3)
                
                logger.debug(f"全面内存清理已完成，总共释放了 {total_cleaned:.2f}MB 内存")
            except Exception as e:
                logger.error(f"全面内存清理失败: {str(e)}")
        
        # 创建并启动线程
        clean_thread = threading.Thread(target=clean_thread_func)
        clean_thread.daemon = True
        clean_thread.start()
        
        # 显示进度对话框
        self.progress_dialog.exec_()
        
        # 清理引用
        self.progress_dialog = None
        
        # 更新状态
        self.update_memory_status()

    @Slot()
    def delete_ace_services(self):
        """删除ACE相关服务"""
        # 确认对话框
        reply = QMessageBox.question(
            self,
            "确认删除反作弊 AntiCheatExpert 服务",
            "此操作将以管理员权限删除以下服务：\n"
            "- ACE-GAME\n"
            "- ACE-BASE\n"
            "- AntiCheatExpert Service\n"
            "- AntiCheatExpert Protection\n\n"
            "这些服务将被永久删除，确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 服务列表
        services = [
            "ACE-GAME",
            "ACE-BASE",
            "AntiCheatExpert Service",
            "AntiCheatExpert Protection"
        ]
        
        # 创建进度对话框
        progress = QProgressDialog("正在删除ACE服务...", "取消", 0, len(services), self)
        progress.setWindowTitle("删除服务")
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        
        # 使用线程执行删除操作
        threading.Thread(target=self._delete_services_thread, args=(services, progress)).start()
    
    def _delete_services_thread(self, services, progress):
        """线程函数：删除服务"""
        results = []
        success_count = 0
        
        for i, service in enumerate(services):
            # 更新进度
            QMetaObject.invokeMethod(
                progress, "setValue", 
                Qt.ConnectionType.QueuedConnection, 
                QGenericArgument("int", i)
            )
            
            # 检查服务是否存在
            exists, status, _ = self.monitor.check_service_status(service)
            if not exists:
                results.append(f"{service}: 服务不存在")
                continue
            
            # 创建提升权限的命令
            try:
                # 创建临时批处理文件
                temp_bat_path = os.path.join(os.environ['TEMP'], f"delete_service_{i}.bat")
                with open(temp_bat_path, 'w') as f:
                    f.write(f'@echo off\nsc stop "{service}"\nsc delete "{service}"\necho 服务删除完成\npause\n')
                
                # 使用管理员权限执行批处理文件
                cmd = f'powershell -Command "Start-Process -Verb RunAs cmd.exe -ArgumentList \'/c \"{temp_bat_path}\"\'\"'
                subprocess.run(cmd, shell=True, check=False)
                
                # 等待操作完成和用户确认
                time.sleep(2)
                
                # 校验服务是否已删除
                exists, _, _ = self.monitor.check_service_status(service)
                if exists:
                    results.append(f"{service}: 删除失败或等待用户确认")
                else:
                    results.append(f"{service}: 已成功删除")
                    success_count += 1
                    
                # 尝试删除临时文件
                try:
                    if os.path.exists(temp_bat_path):
                        os.remove(temp_bat_path)
                except:
                    pass
            except Exception as e:
                logger.error(f"删除服务 {service} 时出错: {str(e)}")
                results.append(f"{service}: 删除出错 - {str(e)}")
        
        # 更新最终进度并关闭进度对话框
        QMetaObject.invokeMethod(
            progress, "setValue", 
            Qt.ConnectionType.QueuedConnection, 
            QGenericArgument("int", len(services))
        )
        
        # 显示结果
        result_text = "\n".join(results)
        QMetaObject.invokeMethod(
            self, "_show_delete_services_result", 
            Qt.ConnectionType.QueuedConnection, 
            QGenericArgument("QString", result_text),
            QGenericArgument("int", success_count),
            QGenericArgument("int", len(services))
        )
    
    @Slot(str, int, int)
    def _show_delete_services_result(self, result_text, success_count, total_count):
        """显示删除服务的结果"""
        QMessageBox.information(
            self,
            "删除服务结果",
            f"操作完成，成功删除 {success_count}/{total_count} 个服务。\n\n详细信息：\n{result_text}"
        )
        
        # 添加通知
        if success_count > 0:
            self.add_message(f"已成功删除 {success_count} 个ACE服务")
            
        # 刷新状态
        self.update_status()

    @Slot()
    def apply_io_priority(self):
        """应用I/O优先级设置"""
        process_name = self.process_combo.currentText()
        if not process_name:
            QMessageBox.warning(self, "错误", "请输入有效的进程名称")
            return
        
        # 获取选择的优先级级别
        priority = self.priority_combo.currentData()
        
        # 获取I/O优先级管理器
        io_manager = get_io_priority_manager()
        
        # 设置进程I/O优先级
        success_count, total_count = io_manager.set_process_io_priority_by_name(process_name, priority)
        
        # 提示是否添加到自动优化列表
        if total_count > 0:
            reply = QMessageBox.question(
                self,
                "添加到自动优化列表",
                f"已成功为 {success_count}/{total_count} 个名为 {process_name} 的进程设置I/O优先级。\n\n"
                f"是否将该进程添加到自动优化列表？\n"
                f"(此列表中的进程会在程序启动和定期检查时自动设置I/O优先级)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.add_to_auto_io_priority_list(process_name, priority)
        else:
            QMessageBox.information(self, "结果", f"未找到名为 {process_name} 的进程")
        
        # 更新状态显示
        self.update_status()
        
    def add_to_auto_io_priority_list(self, process_name, priority):
        """添加进程到自动I/O优先级设置列表"""
        # 检查进程是否已在列表中
        process_exists = False
        for process in self.monitor.config_manager.io_priority_processes:
            if process.get('name') == process_name:
                # 更新优先级
                process['priority'] = priority
                process_exists = True
                break
        
        # 如果不在列表中，则添加
        if not process_exists:
            self.monitor.config_manager.io_priority_processes.append({
                'name': process_name,
                'priority': priority
            })
        
        # 保存配置
        if self.monitor.config_manager.save_config():
            logger.info(f"已将进程 {process_name} 添加到自动I/O优先级设置列表")
            QMessageBox.information(
                self,
                "已添加",
                f"进程 {process_name} 已添加到自动I/O优先级设置列表。\n\n"
                f"程序将在启动时和每隔30秒自动检查并设置该进程的I/O优先级。"
            )
        else:
            logger.error(f"保存I/O优先级设置失败")
            QMessageBox.warning(
                self,
                "保存失败",
                "无法保存I/O优先级设置，请检查程序权限和磁盘空间。"
            )

    @Slot()
    def optimize_anticheat_processes(self):
        """一键优化所有反作弊进程的I/O优先级"""
        # 反作弊相关进程名称列表
        anticheat_processes = [
            "SGuard64.exe",
            "ACE-Tray.exe",
            "AntiCheatExpert.exe",
            "AntiCheatExpertBase.sys",
            "GameAntiCheat.exe",
            "BattlEye.exe",
            "EasyAntiCheat.exe"
        ]
        
        # 获取I/O优先级管理器
        io_manager = get_io_priority_manager()
        
        # 显示进度对话框
        progress = QProgressDialog("正在优化反作弊进程...", "取消", 0, len(anticheat_processes), self)
        progress.setWindowTitle("优化I/O优先级")
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        
        # 初始化结果统计
        total_processes = 0
        successful_processes = 0
        affected_process_names = []
        
        # 为每个进程设置优先级
        for i, process_name in enumerate(anticheat_processes):
            # 更新进度
            progress.setValue(i)
            if progress.wasCanceled():
                break
            
            # 设置为很低优先级
            success_count, count = io_manager.set_process_io_priority_by_name(
                process_name, 
                IO_PRIORITY_HINT.IoPriorityVeryLow
            )
            
            if count > 0:
                total_processes += count
                successful_processes += success_count
                affected_process_names.append(f"{process_name} ({success_count}/{count})")
        
        # 完成进度
        progress.setValue(len(anticheat_processes))
        
        # 显示结果
        if total_processes == 0:
            QMessageBox.information(self, "优化结果", "未找到任何反作弊进程")
        else:
            QMessageBox.information(
                self, 
                "优化结果", 
                f"已成功优化 {successful_processes}/{total_processes} 个反作弊进程\n\n"
                f"受影响的进程: {', '.join(affected_process_names)}"
            )
        
        # 更新状态显示
        self.update_status()

    @Slot()
    def optimize_current_game(self):
        """优化当前游戏体验"""
        # 检查是否有游戏正在运行
        running_games = []
        for game_config in self.monitor.game_configs:
            if game_config.enabled and game_config.main_game_running:
                running_games.append(game_config)
        
        if not running_games:
            QMessageBox.information(self, "提示", "当前没有游戏在运行")
            return
        
        # 获取I/O优先级管理器
        io_manager = get_io_priority_manager()
        
        # 提高游戏进程优先级，降低其他进程优先级的逻辑
        result_messages = []
        
        # 确认操作
        reply = QMessageBox.question(
            self,
            "确认操作",
            "此操作将：\n"
            "1. 降低所有反作弊进程的I/O优先级\n"
            "2. 尽可能提高游戏主进程的响应性\n\n"
            f"检测到正在运行的游戏: {', '.join([g.name for g in running_games])}\n\n"
            "确定要继续吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # 显示进度对话框
        progress = QProgressDialog("正在优化游戏体验...", "取消", 0, 2, self)
        progress.setWindowTitle("优化游戏体验")
        progress.setMinimumDuration(0)
        progress.setValue(0)
        progress.show()
        
        # 1. 降低反作弊进程的I/O优先级
        anticheat_processes = [
            "SGuard64.exe",
            "ACE-Tray.exe",
            "AntiCheatExpert.exe",
            "GameAntiCheat.exe",
            "BattlEye.exe",
            "EasyAntiCheat.exe"
        ]
        
        ac_total = 0
        ac_success = 0
        for process_name in anticheat_processes:
            success, total = io_manager.set_process_io_priority_by_name(
                process_name, 
                IO_PRIORITY_HINT.IoPriorityVeryLow
            )
            ac_total += total
            ac_success += success
        
        if ac_total > 0:
            result_messages.append(f"已降低 {ac_success}/{ac_total} 个反作弊进程的I/O优先级")
        
        progress.setValue(1)
        if progress.wasCanceled():
            return
        
        # 2. 对于当前运行的游戏，确保其主进程有正常或更高的I/O优先级
        game_total = 0
        game_success = 0
        for game in running_games:
            if game.main_game:
                success, total = io_manager.set_process_io_priority_by_name(
                    game.main_game, 
                    IO_PRIORITY_HINT.IoPriorityNormal  # 使用正常优先级
                )
                game_total += total
                game_success += success
        
        if game_total > 0:
            result_messages.append(f"已为 {game_success}/{game_total} 个游戏进程设置正常I/O优先级")
        
        progress.setValue(2)
        
        # 显示结果
        if not result_messages:
            QMessageBox.information(self, "优化结果", "未能优化任何进程")
        else:
            QMessageBox.information(self, "优化结果", "\n".join(result_messages))
        
        # 更新状态显示
        self.update_status()

    @Slot()
    def show_io_priority_list(self):
        """显示I/O优先级进程列表管理对话框"""
        dialog = ProcessIoPriorityListDialog(self, self.monitor.config_manager)
        dialog.exec()


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
        
        # 检查 ACE-Tray.exe 是否存在 (ACE反作弊程序是否安装提示弹窗)
        ace_proc = monitor.is_process_running(monitor.anticheat_name)
        if not ace_proc and monitor.anticheat_killed:
            status_lines.append("✅ ACE-Tray进程：已终止")
        elif not ace_proc:
            status_lines.append("ℹ️ ACE-Tray进程：未运行")
        elif ace_proc and monitor.anticheat_killed:
            status_lines.append("⏳ ACE-Tray进程：处理中")
        else:
            status_lines.append("❗ ACE-Tray进程：需要处理")
        
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
        
        # 检查 AntiCheatExpert Service 服务状态
        service_exists, status, start_type = monitor.check_service_status(monitor.anticheat_service_name)
        if service_exists:
            if status == 'running':
                status_lines.append("✅ AntiCheatExpert服务：正在运行")
            elif status == 'stopped':
                status_lines.append("⚠️ AntiCheatExpert服务：已停止")
            else:
                status_lines.append(f"ℹ️ AntiCheatExpert服务：{status}")
            
            # 显示启动类型
            status_lines.append(f"⚙️ 服务启动类型：{get_start_type_display(start_type)}")
        else:
            status_lines.append("❓ AntiCheatExpert服务：未找到")
    else:
        status_lines.append("🎮 游戏主程序：未运行")
    
    status_lines.append("\n⚙️ 系统设置：")
    status_lines.append("  🔔 通知状态：" + ("开启" if monitor.show_notifications else "关闭"))
    status_lines.append(f"  🔁 开机自启：{'开启' if monitor.auto_start else '关闭'}")
    status_lines.append(f"  🐛 调试模式：{'开启' if monitor.config_manager.debug_mode else '关闭'}")
    status_lines.append(f"  📁 配置目录：{monitor.config_manager.config_dir}")
    status_lines.append(f"  📝 日志目录：{monitor.config_manager.log_dir}")
    status_lines.append(f"  ⏱️ 日志保留：{monitor.config_manager.log_retention_days}天")
    
    return "\n".join(status_lines)


def get_start_type_display(start_type):
    """获取启动类型的显示名称"""
    if start_type == 'auto':
        return "自动启动"
    elif start_type == 'disabled':
        return "已禁用"
    elif start_type == 'manual':
        return "手动"
    elif start_type == 'boot':
        return "系统启动"
    elif start_type == 'system':
        return "系统"
    else:
        return start_type


def create_gui(monitor, icon_path=None):
    """
    创建图形用户界面
    
    Args:
        monitor: 进程监控器对象
        icon_path: 图标路径
        
    Returns:
        (QApplication, MainWindow): 应用程序对象和主窗口对象
    """
    
    qdarktheme.enable_hi_dpi()
    
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        
    # 检测系统主题
    system_theme = "dark" if darkdetect.isDark() else "light"
    
    qdarktheme.setup_theme(system_theme)
    
    window = MainWindow(monitor, icon_path)
    return app, window