#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
进程I/O优先级管理界面模块
"""

import os
import threading
import time
import psutil
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QComboBox, QLineEdit, QGroupBox, QCheckBox, QProgressBar,
    QMessageBox, QTabWidget, QWidget, QSpinBox, QSplitter,
    QTextEdit, QFrame, QProgressDialog, QButtonGroup, QRadioButton
)
from PySide6.QtCore import Qt, Signal, QTimer, QThread
from PySide6.QtGui import QIcon, QFont, QPalette, QColor
from loguru import logger

from utils.process_io_priority import get_io_priority_manager, IO_PRIORITY_HINT, PERFORMANCE_MODE


class ProcessInfoWorker(QThread):
    """获取进程信息的工作线程"""
    
    # 信号：进程数据更新
    processes_updated = Signal(list)
    # 信号：进度更新
    progress_updated = Signal(int, int)  # (current, total)
    
    def __init__(self):
        super().__init__()
        self.should_stop = False
        
    def run(self):
        """获取所有进程信息"""
        try:
            processes = []
            all_processes = list(psutil.process_iter())
            total_processes = len(all_processes)
            
            for i, proc in enumerate(all_processes):
                if self.should_stop:
                    break
                    
                try:
                    # 发送进度更新
                    self.progress_updated.emit(i + 1, total_processes)
                    
                    # 获取进程基本信息
                    proc_info = proc.as_dict(attrs=[
                        'pid', 'name', 'username', 'status',
                        'create_time', 'memory_percent'
                    ])
                    
                    # 获取内存信息
                    try:
                        memory_info = proc.memory_info()
                        proc_info['memory_mb'] = memory_info.rss / (1024 * 1024)
                    except:
                        proc_info['memory_mb'] = 0
                    
                    # 处理用户名
                    if not proc_info.get('username'):
                        proc_info['username'] = 'N/A'
                    
                    # 处理进程名
                    if not proc_info.get('name'):
                        proc_info['name'] = f'PID-{proc_info["pid"]}'
                    
                    # 判断是否为系统进程
                    username = proc_info.get('username', '')
                    proc_info['is_system'] = username in [
                        'NT AUTHORITY\\SYSTEM', 'NT AUTHORITY\\LOCAL SERVICE', 
                        'NT AUTHORITY\\NETWORK SERVICE', 'N/A'
                    ]
                    
                    processes.append(proc_info)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    logger.debug(f"获取进程信息失败: {e}")
                    continue
            
            # 按内存使用量排序
            processes.sort(key=lambda x: x.get('memory_mb', 0), reverse=True)
            
            # 发送结果
            if not self.should_stop:
                self.processes_updated.emit(processes)
                
        except Exception as e:
            logger.error(f"获取进程信息时发生错误: {e}")
            
    def stop(self):
        """停止工作线程"""
        self.should_stop = True


class ProcessIoPriorityManagerDialog(QDialog):
    """进程I/O优先级管理对话框"""
    
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.io_manager = get_io_priority_manager()
        self.process_worker = None
        self.all_processes = []
        self.filtered_processes = []
        
        # 防抖动定时器
        self.filter_timer = QTimer()
        self.filter_timer.setSingleShot(True)
        self.filter_timer.timeout.connect(self._apply_filters)
        
        self.setup_ui()
        self.setup_timer()
        self.load_auto_optimize_list()
        
        # 延迟加载进程列表，避免阻塞UI
        QTimer.singleShot(100, self.refresh_process_list)
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("进程I/O优先级管理")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        layout = QVBoxLayout(self)
        
        # 创建选项卡
        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)
        
        # 进程列表选项卡
        process_tab = self.create_process_tab()
        tab_widget.addTab(process_tab, "🔍 进程列表")
        
        # 自动优化列表选项卡
        auto_optimize_tab = self.create_auto_optimize_tab()
        tab_widget.addTab(auto_optimize_tab, "⚙️ 自动优化列表")
        
        # 底部按钮
        button_layout = QHBoxLayout()
        
        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新进程列表")
        self.refresh_btn.clicked.connect(self.refresh_process_list)
        button_layout.addWidget(self.refresh_btn)
        
        button_layout.addStretch()
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def create_process_tab(self):
        """创建进程列表选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 顶部过滤器组
        filter_group = QGroupBox("🔍 过滤器")
        filter_layout = QVBoxLayout(filter_group)
        
        # 第一行过滤器
        filter_row1 = QHBoxLayout()
        
        # 进程名过滤
        filter_row1.addWidget(QLabel("进程名:"))
        self.name_filter = QLineEdit()
        self.name_filter.setPlaceholderText("输入进程名称进行过滤...")
        self.name_filter.textChanged.connect(self._schedule_filter)
        filter_row1.addWidget(self.name_filter)
        
        # 内存过滤
        filter_row1.addWidget(QLabel("内存大于:"))
        self.memory_filter = QSpinBox()
        self.memory_filter.setRange(0, 10000)
        self.memory_filter.setValue(10)  # 默认显示内存大于10MB的进程
        self.memory_filter.setSuffix(" MB")
        self.memory_filter.valueChanged.connect(self._schedule_filter)
        filter_row1.addWidget(self.memory_filter)
        
        filter_layout.addLayout(filter_row1)
        
        # 第二行过滤器
        filter_row2 = QHBoxLayout()
        
        # 进程类型过滤
        filter_row2.addWidget(QLabel("进程类型:"))
        self.process_type_group = QButtonGroup()
        
        self.show_all_radio = QRadioButton("全部")
        self.show_all_radio.setChecked(True)
        self.show_all_radio.toggled.connect(self._schedule_filter)
        self.process_type_group.addButton(self.show_all_radio)
        filter_row2.addWidget(self.show_all_radio)
        
        self.show_user_radio = QRadioButton("用户进程")
        self.show_user_radio.toggled.connect(self._schedule_filter)
        self.process_type_group.addButton(self.show_user_radio)
        filter_row2.addWidget(self.show_user_radio)
        
        self.show_system_radio = QRadioButton("系统进程")
        self.show_system_radio.toggled.connect(self._schedule_filter)
        self.process_type_group.addButton(self.show_system_radio)
        filter_row2.addWidget(self.show_system_radio)
        
        filter_row2.addStretch()
        
        # 清除过滤器按钮
        clear_filter_btn = QPushButton("清除过滤器")
        clear_filter_btn.clicked.connect(self.clear_filters)
        filter_row2.addWidget(clear_filter_btn)
        
        filter_layout.addLayout(filter_row2)
        layout.addWidget(filter_group)
        
        # 信息行
        info_layout = QHBoxLayout()
        self.process_count_label = QLabel("进程数量: 0")
        info_layout.addWidget(self.process_count_label)
        
        self.loading_progress = QProgressBar()
        self.loading_progress.setVisible(False)
        self.loading_progress.setMaximumHeight(20)
        info_layout.addWidget(self.loading_progress)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # 进程表格
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(9)
        self.process_table.setHorizontalHeaderLabels([
            "PID", "进程名", "用户", "状态", "内存(MB)", "创建时间", "优先级设置", "性能模式", "操作"
        ])
        
        # 设置表格属性
        self.process_table.setAlternatingRowColors(True)
        self.process_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.process_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.process_table.setSortingEnabled(True)
        self.process_table.setShowGrid(True)
        self.process_table.setFocusPolicy(Qt.NoFocus)  # 禁用焦点，避免蓝色焦点框
        self.process_table.setSelectionMode(QAbstractItemView.SingleSelection)  # 单选模式
        self.process_table.clearSelection()  # 清除任何默认选择
        
        # 设置表格字体
        font = QFont()
        font.setPointSize(9)
        self.process_table.setFont(font)
        
        # 设置列宽
        header = self.process_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # PID
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # 进程名
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # 用户
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # 状态
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # 内存
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # 创建时间
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # 优先级设置
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # 性能模式
        header.setSectionResizeMode(8, QHeaderView.Fixed)  # 操作
        header.resizeSection(8, 120)  # 设置操作列宽度为120像素
        
        # 设置行高
        self.process_table.verticalHeader().setDefaultSectionSize(35)
        
        layout.addWidget(self.process_table)
        
        return widget
    
    def create_auto_optimize_tab(self):
        """创建自动优化列表选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 说明信息
        info_label = QLabel(
            "自动优化列表中的进程会在程序启动时和每隔30秒自动完整优化。\n"
            "优化包括：I/O优先级设置、CPU优先级降低、CPU亲和性调整、效能模式启用。\n"
            "这有助于持续优化这些进程的系统资源占用，减少对前台应用的影响。"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 自动优化列表表格
        self.auto_optimize_table = QTableWidget()
        self.auto_optimize_table.setColumnCount(5)
        self.auto_optimize_table.setHorizontalHeaderLabels([
            "进程名", "I/O优先级", "性能模式", "添加时间", "操作"
        ])
        
        # 设置表格属性
        self.auto_optimize_table.setAlternatingRowColors(True)
        self.auto_optimize_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.auto_optimize_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.auto_optimize_table.setShowGrid(True)
        self.auto_optimize_table.setFocusPolicy(Qt.NoFocus)  # 禁用焦点，避免蓝色焦点框
        
        # 设置表格字体
        font = QFont()
        font.setPointSize(9)
        self.auto_optimize_table.setFont(font)
        
        # 设置列宽
        auto_header = self.auto_optimize_table.horizontalHeader()
        auto_header.setSectionResizeMode(0, QHeaderView.Stretch)
        auto_header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        auto_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        auto_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        auto_header.setSectionResizeMode(4, QHeaderView.Fixed)  # 操作
        auto_header.resizeSection(4, 120)  # 设置操作列宽度为100像素
        
        # 设置行高
        self.auto_optimize_table.verticalHeader().setDefaultSectionSize(35)
        
        layout.addWidget(self.auto_optimize_table)
        
        # 底部统计信息
        stats_layout = QHBoxLayout()
        self.auto_optimize_count_label = QLabel("自动优化进程数: 0")
        stats_layout.addWidget(self.auto_optimize_count_label)
        stats_layout.addStretch()
        
        # 清空列表按钮
        clear_all_btn = QPushButton("🗑️ 清空列表")
        clear_all_btn.clicked.connect(self.clear_auto_optimize_list)
        stats_layout.addWidget(clear_all_btn)
        
        layout.addLayout(stats_layout)
        
        return widget
    
    def setup_timer(self):
        """设置定时器"""
        # 定时刷新进程信息（每30秒）
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_process_list)
        self.refresh_timer.start(30000)  # 30秒
    
    def _schedule_filter(self):
        """安排过滤操作（防抖动）"""
        self.filter_timer.stop()
        self.filter_timer.start(300)  # 300毫秒后执行过滤
    
    def _apply_filters(self):
        """应用过滤器（实际的过滤逻辑）"""
        if not self.all_processes:
            return
        
        name_filter = self.name_filter.text().lower().strip()
        memory_filter = self.memory_filter.value()
        
        # 进程类型过滤
        show_all = self.show_all_radio.isChecked()
        show_user = self.show_user_radio.isChecked()
        show_system = self.show_system_radio.isChecked()
        
        # 过滤进程
        filtered_processes = []
        for proc in self.all_processes:
            # 进程名过滤
            if name_filter and name_filter not in proc['name'].lower():
                continue
            
            # 内存过滤
            if proc.get('memory_mb', 0) < memory_filter:
                continue
            
            # 进程类型过滤
            if not show_all:
                if show_user and proc.get('is_system', False):
                    continue
                if show_system and not proc.get('is_system', False):
                    continue
            
            filtered_processes.append(proc)
        
        self.filtered_processes = filtered_processes
        
        # 更新表格
        self.populate_process_table(filtered_processes)
        
        # 更新统计信息
        self.process_count_label.setText(
            f"显示进程数: {len(filtered_processes)} / 总进程数: {len(self.all_processes)}"
        )
    
    def clear_filters(self):
        """清除所有过滤器"""
        self.name_filter.clear()
        self.memory_filter.setValue(0)
        self.show_all_radio.setChecked(True)
        self._apply_filters()
    
    def refresh_process_list(self):
        """刷新进程列表"""
        if self.process_worker and self.process_worker.isRunning():
            return  # 如果已经在刷新，则跳过
        
        # 显示加载状态
        self.loading_progress.setVisible(True)
        self.loading_progress.setRange(0, 0)  # 不确定进度
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("🔄 刷新中...")
        
        # 创建工作线程
        self.process_worker = ProcessInfoWorker()
        self.process_worker.processes_updated.connect(self.update_process_table)
        self.process_worker.progress_updated.connect(self.update_loading_progress)
        self.process_worker.finished.connect(self.on_refresh_finished)
        self.process_worker.start()
    
    def update_loading_progress(self, current, total):
        """更新加载进度"""
        if total > 0:
            self.loading_progress.setRange(0, total)
            self.loading_progress.setValue(current)
    
    def on_refresh_finished(self):
        """刷新完成"""
        self.loading_progress.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.refresh_btn.setText("🔄 刷新进程列表")
        
        if self.process_worker:
            self.process_worker.deleteLater()
            self.process_worker = None
    
    def update_process_table(self, processes):
        """更新进程表格"""
        self.all_processes = processes
        self._apply_filters()  # 应用当前过滤器
    
    def populate_process_table(self, processes):
        """填充进程表格（优化版本）"""
        # 禁用排序以提高性能
        self.process_table.setSortingEnabled(False)
        
        # 设置行数
        current_row_count = self.process_table.rowCount()
        target_row_count = len(processes)
        
        if current_row_count != target_row_count:
            self.process_table.setRowCount(target_row_count)
        
        # 批量更新表格项
        for row, proc in enumerate(processes):
            self._populate_row(row, proc)
        
        # 重新启用排序
        self.process_table.setSortingEnabled(True)
    
    def _populate_row(self, row, proc):
        """填充单行数据"""
        # PID
        pid_item = self._get_or_create_item(row, 0)
        pid_item.setText(str(proc['pid']))
        pid_item.setData(Qt.UserRole, proc)  # 存储完整进程信息
        
        # 进程名
        name_item = self._get_or_create_item(row, 1)
        name_item.setText(proc['name'])
        
        # 用户
        user_item = self._get_or_create_item(row, 2)
        user_item.setText(proc['username'])
        
        # 状态
        status_item = self._get_or_create_item(row, 3)
        status_item.setText(proc['status'])
        
        # 内存
        memory_item = self._get_or_create_item(row, 4)
        memory_mb = proc.get('memory_mb', 0)
        memory_item.setText(f"{memory_mb:.1f}")
        
        # 创建时间
        time_item = self._get_or_create_item(row, 5)
        try:
            create_time = time.strftime('%m-%d %H:%M', 
                                      time.localtime(proc.get('create_time', 0)))
        except:
            create_time = 'N/A'
        time_item.setText(create_time)
        
        # 优先级设置下拉框
        priority_combo = self.process_table.cellWidget(row, 6)
        if not priority_combo:
            priority_combo = QComboBox()
            
            # 按优先级从高到低排列，便于用户理解
            priority_combo.addItem("🔴 最高优先级", IO_PRIORITY_HINT.IoPriorityCritical)
            priority_combo.addItem("🟢 正常优先级", IO_PRIORITY_HINT.IoPriorityNormal)  
            priority_combo.addItem("🟡 低优先级", IO_PRIORITY_HINT.IoPriorityLow)
            priority_combo.addItem("🔵 最低优先级", IO_PRIORITY_HINT.IoPriorityVeryLow)
            
            priority_combo.setCurrentIndex(1)  # 默认选择"正常先级"
            priority_combo.setMaximumHeight(50)
            
            # 设置改进的工具提示
            priority_combo.setToolTip(
                "选择进程I/O优先级：\n\n"
                "🔴 最高优先级 - 最高I/O优先级，适用于关键系统进程\n"
                "🟢 正常优先级 - 系统默认I/O优先级\n" 
                "🟡 低优先级 - 降低磁盘I/O优先级，减少对系统影响\n"
                "🔵 最低优先级 - 最低I/O优先级，推荐用于后台进程\n\n"
                "💡 建议：\n"
                "• 游戏/重要应用：正常或最高\n"
                "• 后台进程/反作弊：最低或低\n"
                "• 一般应用：正常"
            )
            self.process_table.setCellWidget(row, 6, priority_combo)
        
        # 性能模式选择
        performance_mode_combo = self.process_table.cellWidget(row, 7)
        if not performance_mode_combo:
            performance_mode_combo = QComboBox()
            performance_mode_combo.addItem("🔥 最大性能模式", PERFORMANCE_MODE.MAXIMUM_PERFORMANCE)
            performance_mode_combo.addItem("🚀 高性能模式", PERFORMANCE_MODE.HIGH_PERFORMANCE)
            performance_mode_combo.addItem("🍉 正常模式", PERFORMANCE_MODE.NORMAL_MODE)
            performance_mode_combo.addItem("🌱 效能模式", PERFORMANCE_MODE.ECO_MODE)
            performance_mode_combo.setCurrentIndex(2)  # 默认选择"正常模式"
            performance_mode_combo.setMaximumHeight(40)
            
            # 设置改进的工具提示
            performance_mode_combo.setToolTip(
                "选择进程性能模式：\n\n"
                "🔥 最大性能模式 - 实时优先级，最高性能但可能影响系统稳定性\n"
                "🚀 高性能模式 - 高优先级，适合游戏等重要应用\n"
                "🍉 正常模式 - 系统默认设置\n"
                "🌱 效能模式 - 降低性能和功耗，适合后台进程\n\n"
                "💡 建议：\n"
                "• 游戏/重要应用：高性能或最大性能\n"
                "• 后台进程/反作弊：效能模式\n"
                "• 一般应用：正常模式"
            )
            self.process_table.setCellWidget(row, 7, performance_mode_combo)
        
        # 操作按钮
        action_widget = self.process_table.cellWidget(row, 8)
        if not action_widget:
            action_layout = QHBoxLayout()
            action_widget = QWidget()
            
            # 应用并添加到列表按钮（合并功能）
            apply_btn = QPushButton("🚀 应用")
            apply_btn.setMaximumWidth(100)  # 增加按钮宽度
            apply_btn.setMaximumHeight(28)
            apply_btn.setToolTip("应用当前选择的I/O优先级和性能模式设置到进程，并添加到自动优化列表")
            apply_btn.clicked.connect(lambda checked, r=row: self.apply_io_priority(r))
            action_layout.addWidget(apply_btn)
            
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.setSpacing(2)
            action_widget.setLayout(action_layout)
            self.process_table.setCellWidget(row, 8, action_widget)
    
    def _get_or_create_item(self, row, column):
        """获取或创建表格项"""
        item = self.process_table.item(row, column)
        if not item:
            item = QTableWidgetItem()
            self.process_table.setItem(row, column, item)
        return item
    
    def apply_io_priority(self, row):
        """完整优化进程并添加到自动优化列表"""
        # 获取进程信息
        pid_item = self.process_table.item(row, 0)
        if not pid_item:
            return
        
        proc_info = pid_item.data(Qt.UserRole)
        if not proc_info:
            return
        
        # 获取选择的优先级
        priority_combo = self.process_table.cellWidget(row, 6)
        if not priority_combo:
            return
        
        # 获取选择的性能模式
        performance_mode_combo = self.process_table.cellWidget(row, 7)
        if not performance_mode_combo:
            return
        
        priority = priority_combo.currentData()
        performance_mode = performance_mode_combo.currentData()
        process_name = proc_info['name']
        pid = proc_info['pid']
        
        # 第一步：完整优化进程（I/O优先级 + CPU优先级 + 性能模式）
        success = self.io_manager.set_process_io_priority(pid, priority, performance_mode)
        
        if not success:
            QMessageBox.warning(self, "优化失败", 
                f"无法优化进程 {process_name} (PID: {pid})\n可能是权限不足或进程已退出")
            return
        
        # 第二步：添加到自动优化列表
        # 检查是否已存在
        existing_found = False
        for existing_proc in self.config_manager.io_priority_processes:
            if existing_proc.get('name') == process_name:
                # 如果进程已存在，询问是否更新
                if (existing_proc.get('priority') != priority or 
                    existing_proc.get('performance_mode', PERFORMANCE_MODE.ECO_MODE) != performance_mode):
                    reply = QMessageBox.question(
                        self,
                        "进程已存在",
                        f"进程 {process_name} 已在自动优化列表中，但设置不同。\n"
                        f"当前列表中优先级: {self.get_priority_text(existing_proc.get('priority', 0))}\n"
                        f"新选择的优先级: {self.get_priority_text(priority)}\n"
                        f"当前列表中性能模式: {self.get_performance_mode_text(existing_proc.get('performance_mode', PERFORMANCE_MODE.ECO_MODE))}\n"
                        f"新选择的性能模式: {self.get_performance_mode_text(performance_mode)}\n\n"
                        f"是否要更新设置？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    if reply == QMessageBox.Yes:
                        existing_proc['priority'] = priority
                        existing_proc['performance_mode'] = performance_mode
                        existing_proc['updated_time'] = time.time()
                        existing_found = True
                    else:
                        # 用户选择不更新，但进程优化已经完成了
                        QMessageBox.information(self, "优化完成", 
                            f"✅ 已成功完整优化进程 {process_name} (PID: {pid})\n"
                            f"⚡ I/O优先级: {self.get_priority_text(priority)}\n"
                            f"⚡ 性能模式: {self.get_performance_mode_text(performance_mode)}\n\n"
                            f"自动优化列表保持原有设置不变")
                        return
                else:
                    # 设置相同，无需更新
                    existing_found = True
                break
        
        if not existing_found:
            # 添加新进程到列表
            self.config_manager.io_priority_processes.append({
                'name': process_name,
                'priority': priority,
                'performance_mode': performance_mode,
                'added_time': time.time()
            })
        
        # 第三步：保存配置
        if self.config_manager.save_config():
            if existing_found:
                QMessageBox.information(self, "优化成功", 
                    f"✅ 已成功完整优化进程 {process_name} (PID: {pid})\n"
                    f"⚡ I/O优先级: {self.get_priority_text(priority)}\n"
                    f"⚡ 性能模式: {self.get_performance_mode_text(performance_mode)}\n\n"
                    f"✅ 自动优化列表中的设置已更新")
            else:
                QMessageBox.information(self, "优化成功", 
                    f"✅ 已成功完整优化进程 {process_name} (PID: {pid})\n"
                    f"⚡ I/O优先级: {self.get_priority_text(priority)}\n"
                    f"⚡ 性能模式: {self.get_performance_mode_text(performance_mode)}\n\n"
                    f"✅ 已添加到自动优化列表，将定期自动优化")
            
            # 刷新自动优化列表显示
            self.load_auto_optimize_list()
            logger.debug(f"完整优化并添加进程到自动优化列表: {process_name} (PID: {pid}) -> {priority}, {performance_mode}")
        else:
            QMessageBox.warning(self, "保存失败", 
                f"进程优化成功，但无法保存到自动优化列表\n请检查程序权限")
    
    def load_auto_optimize_list(self):
        """加载自动优化列表（优化版本）"""
        if not self.config_manager:
            return
        
        processes = self.config_manager.io_priority_processes
        
        # 禁用排序以提高性能
        self.auto_optimize_table.setSortingEnabled(False)
        
        current_row_count = self.auto_optimize_table.rowCount()
        target_row_count = len(processes)
        
        if current_row_count != target_row_count:
            self.auto_optimize_table.setRowCount(target_row_count)
        
        for row, proc in enumerate(processes):
            # 进程名
            name_item = self._get_or_create_auto_item(row, 0)
            name_item.setText(proc.get('name', ''))
            
            # 优先级
            priority = proc.get('priority', 0)
            priority_text = self.get_priority_text(priority)
            priority_item = self._get_or_create_auto_item(row, 1)
            priority_item.setText(priority_text)
            
            # 性能模式
            performance_mode = proc.get('performance_mode', PERFORMANCE_MODE.ECO_MODE)
            performance_mode_text = self.get_performance_mode_text(performance_mode)
            performance_mode_item = self._get_or_create_auto_item(row, 2)
            performance_mode_item.setText(performance_mode_text)
            
            # 添加时间
            add_time = proc.get('added_time', proc.get('updated_time', 0))
            time_item = self._get_or_create_auto_item(row, 3)
            if add_time:
                time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(add_time))
            else:
                time_str = 'N/A'
            time_item.setText(time_str)
            
            # 操作按钮
            action_widget = self.auto_optimize_table.cellWidget(row, 4)
            if not action_widget:
                action_layout = QHBoxLayout()
                action_widget = QWidget()
                
                # 删除按钮
                delete_btn = QPushButton("🗑️ 删除")
                delete_btn.setMaximumWidth(100)  # 增加按钮宽度
                delete_btn.setMaximumHeight(25)
                delete_btn.clicked.connect(lambda checked, r=row: self.delete_from_auto_optimize_list(r))
                action_layout.addWidget(delete_btn)
                
                action_layout.setContentsMargins(2, 2, 2, 2)
                action_layout.setSpacing(2)
                action_widget.setLayout(action_layout)
                self.auto_optimize_table.setCellWidget(row, 4, action_widget)
        
        # 重新启用排序
        self.auto_optimize_table.setSortingEnabled(True)
        
        # 清除选择，避免焦点高亮
        self.auto_optimize_table.clearSelection()
        
        # 更新统计信息
        self.auto_optimize_count_label.setText(f"自动优化进程数: {len(processes)}")
    
    def _get_or_create_auto_item(self, row, column):
        """获取或创建自动优化表格项"""
        item = self.auto_optimize_table.item(row, column)
        if not item:
            item = QTableWidgetItem()
            self.auto_optimize_table.setItem(row, column, item)
        return item
    
    def get_priority_text(self, priority):
        """获取优先级的文本表示"""
        priority_map = {
            IO_PRIORITY_HINT.IoPriorityCritical: "🔴 最高优先级",
            IO_PRIORITY_HINT.IoPriorityNormal: "🟢 正常优先级", 
            IO_PRIORITY_HINT.IoPriorityLow: "🟡 低优先级",
            IO_PRIORITY_HINT.IoPriorityVeryLow: "🔵 最低优先级"
        }
        return priority_map.get(priority, f"未知({priority})")
    
    def get_performance_mode_text(self, performance_mode):
        """获取性能模式的文本表示"""
        mode_map = {
            PERFORMANCE_MODE.MAXIMUM_PERFORMANCE: "🔥 最大性能模式",
            PERFORMANCE_MODE.HIGH_PERFORMANCE: "🚀 高性能模式",
            PERFORMANCE_MODE.NORMAL_MODE: "🍉 正常模式",
            PERFORMANCE_MODE.ECO_MODE: "🌱 效能模式"
        }
        return mode_map.get(performance_mode, f"未知({performance_mode})")
    
    def delete_from_auto_optimize_list(self, row):
        """从自动优化列表中删除进程"""
        if row < 0 or row >= len(self.config_manager.io_priority_processes):
            return
        
        process_name = self.config_manager.io_priority_processes[row].get('name', '')
        
        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要从自动优化列表中删除进程 '{process_name}' 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            del self.config_manager.io_priority_processes[row]
            
            # 保存配置
            if self.config_manager.save_config():
                self.load_auto_optimize_list()  # 重新加载列表
                logger.debug(f"从自动优化列表删除进程: {process_name}")
            else:
                QMessageBox.warning(self, "保存失败", "删除进程后保存配置失败")
    
    def clear_auto_optimize_list(self):
        """清空自动优化列表"""
        if not self.config_manager.io_priority_processes:
            QMessageBox.information(self, "提示", "自动优化列表已为空")
            return
        
        reply = QMessageBox.question(
            self,
            "确认清空",
            f"确定要清空整个自动优化列表吗？\n这将删除 {len(self.config_manager.io_priority_processes)} 个进程的自动优化设置。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.config_manager.io_priority_processes.clear()
            
            # 保存配置
            if self.config_manager.save_config():
                self.load_auto_optimize_list()  # 重新加载列表
                QMessageBox.information(self, "成功", "已清空自动优化列表")
                logger.debug("清空自动优化列表")
            else:
                QMessageBox.warning(self, "保存失败", "清空列表后保存配置失败")
    
    def closeEvent(self, event):
        """关闭事件处理"""
        # 停止定时器
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        
        if hasattr(self, 'filter_timer'):
            self.filter_timer.stop()
        
        # 停止工作线程
        if self.process_worker and self.process_worker.isRunning():
            self.process_worker.stop()
            self.process_worker.wait(1000)
        
        event.accept()


def show_process_io_priority_manager(parent=None, config_manager=None):
    """显示进程I/O优先级管理对话框"""
    dialog = ProcessIoPriorityManagerDialog(parent, config_manager)
    return dialog.exec() 