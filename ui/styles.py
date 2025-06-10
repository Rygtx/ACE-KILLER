#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
UI样式定义文件 - Ant Design风格
统一管理所有界面样式，支持明暗主题切换
"""


class AntColors:
    """Ant Design 颜色系统 - 浅色主题"""
    
    # 主色系
    PRIMARY_1 = "#e6f7ff"       # 最浅蓝
    PRIMARY_2 = "#bae7ff"       # 浅蓝
    PRIMARY_3 = "#91d5ff"       # 较浅蓝
    PRIMARY_4 = "#69c0ff"       # 中浅蓝
    PRIMARY_5 = "#40a9ff"       # 中蓝
    PRIMARY_6 = "#1890ff"       # 主蓝色
    PRIMARY_7 = "#096dd9"       # 中深蓝
    PRIMARY_8 = "#0050b3"       # 深蓝
    PRIMARY_9 = "#003a8c"       # 较深蓝
    PRIMARY_10 = "#002766"      # 最深蓝
    
    # 成功色系
    SUCCESS_1 = "#f6ffed"       # 最浅绿
    SUCCESS_2 = "#d9f7be"       # 浅绿
    SUCCESS_3 = "#b7eb8f"       # 较浅绿
    SUCCESS_4 = "#95de64"       # 中浅绿
    SUCCESS_5 = "#73d13d"       # 中绿
    SUCCESS_6 = "#52c41a"       # 主绿色
    SUCCESS_7 = "#389e0d"       # 中深绿
    SUCCESS_8 = "#237804"       # 深绿
    SUCCESS_9 = "#135200"       # 较深绿
    SUCCESS_10 = "#092b00"      # 最深绿
    
    # 警告色系
    WARNING_1 = "#fffbe6"       # 最浅橙
    WARNING_2 = "#fff1b8"       # 浅橙
    WARNING_3 = "#ffe58f"       # 较浅橙
    WARNING_4 = "#ffd666"       # 中浅橙
    WARNING_5 = "#ffc53d"       # 中橙
    WARNING_6 = "#faad14"       # 主橙色
    WARNING_7 = "#d48806"       # 中深橙
    WARNING_8 = "#ad6800"       # 深橙
    WARNING_9 = "#874d00"       # 较深橙
    WARNING_10 = "#613400"      # 最深橙
    
    # 错误色系
    ERROR_1 = "#fff2f0"         # 最浅红
    ERROR_2 = "#ffccc7"         # 浅红
    ERROR_3 = "#ffa39e"         # 较浅红
    ERROR_4 = "#ff7875"         # 中浅红
    ERROR_5 = "#ff4d4f"         # 中红
    ERROR_6 = "#f5222d"         # 主红色
    ERROR_7 = "#cf1322"         # 中深红
    ERROR_8 = "#a8071a"         # 深红
    ERROR_9 = "#820014"         # 较深红
    ERROR_10 = "#5c0011"        # 最深红
    
    # 中性色系
    GRAY_1 = "#ffffff"          # 白色
    GRAY_2 = "#fafafa"          # 最浅灰
    GRAY_3 = "#f5f5f5"          # 浅灰
    GRAY_4 = "#f0f0f0"          # 较浅灰
    GRAY_5 = "#d9d9d9"          # 中浅灰
    GRAY_6 = "#bfbfbf"          # 中灰
    GRAY_7 = "#8c8c8c"          # 中深灰
    GRAY_8 = "#595959"          # 深灰
    GRAY_9 = "#434343"          # 较深灰
    GRAY_10 = "#262626"         # 最深灰
    GRAY_11 = "#1f1f1f"         # 近黑
    GRAY_12 = "#141414"         # 黑色
    GRAY_13 = "#000000"         # 纯黑


class AntColorsDark:
    """Ant Design 颜色系统 - 深色主题"""
    
    # 主色系 (保持相对一致，稍微调亮)
    PRIMARY_1 = "#111b26"       # 最深蓝背景
    PRIMARY_2 = "#112545"       # 深蓝背景
    PRIMARY_3 = "#15325b"       # 较深蓝背景
    PRIMARY_4 = "#1554ad"       # 中深蓝
    PRIMARY_5 = "#1668dc"       # 中蓝
    PRIMARY_6 = "#1890ff"       # 主蓝色 (保持)
    PRIMARY_7 = "#40a9ff"       # 较亮蓝
    PRIMARY_8 = "#69c0ff"       # 亮蓝
    PRIMARY_9 = "#91d5ff"       # 很亮蓝
    PRIMARY_10 = "#bae7ff"      # 最亮蓝
    
    # 成功色系
    SUCCESS_1 = "#162312"       # 最深绿背景
    SUCCESS_2 = "#1b2618"       # 深绿背景
    SUCCESS_3 = "#274b32"       # 较深绿背景
    SUCCESS_4 = "#389e0d"       # 中深绿
    SUCCESS_5 = "#52c41a"       # 主绿色 (保持)
    SUCCESS_6 = "#73d13d"       # 较亮绿
    SUCCESS_7 = "#95de64"       # 亮绿
    SUCCESS_8 = "#b7eb8f"       # 很亮绿
    SUCCESS_9 = "#d9f7be"       # 最亮绿
    SUCCESS_10 = "#f6ffed"      # 绿色高亮
    
    # 警告色系
    WARNING_1 = "#2b1d11"       # 最深橙背景
    WARNING_2 = "#342209"       # 深橙背景
    WARNING_3 = "#593716"       # 较深橙背景
    WARNING_4 = "#ad6800"       # 中深橙
    WARNING_5 = "#d48806"       # 中橙
    WARNING_6 = "#faad14"       # 主橙色 (保持)
    WARNING_7 = "#ffc53d"       # 较亮橙
    WARNING_8 = "#ffd666"       # 亮橙
    WARNING_9 = "#ffe58f"       # 很亮橙
    WARNING_10 = "#fff1b8"      # 最亮橙
    
    # 错误色系
    ERROR_1 = "#2a1215"         # 最深红背景
    ERROR_2 = "#431418"         # 深红背景
    ERROR_3 = "#58181c"         # 较深红背景
    ERROR_4 = "#a8071a"         # 中深红
    ERROR_5 = "#cf1322"         # 中红
    ERROR_6 = "#f5222d"         # 主红色 (保持)
    ERROR_7 = "#ff4d4f"         # 较亮红
    ERROR_8 = "#ff7875"         # 亮红
    ERROR_9 = "#ffa39e"         # 很亮红
    ERROR_10 = "#ffccc7"        # 最亮红
    
    # 中性色系 (反转)
    GRAY_1 = "#141414"          # 深色背景
    GRAY_2 = "#1f1f1f"          # 较深背景
    GRAY_3 = "#262626"          # 中深背景
    GRAY_4 = "#434343"          # 较浅背景
    GRAY_5 = "#595959"          # 中浅灰
    GRAY_6 = "#8c8c8c"          # 中灰
    GRAY_7 = "#bfbfbf"          # 中亮灰
    GRAY_8 = "#d9d9d9"          # 亮灰
    GRAY_9 = "#f0f0f0"          # 很亮灰
    GRAY_10 = "#f5f5f5"         # 最亮灰
    GRAY_11 = "#fafafa"         # 近白
    GRAY_12 = "#ffffff"         # 白色
    GRAY_13 = "#ffffff"         # 纯白


class ThemeManager:
    """主题管理器"""
    
    _current_theme = "light"  # 默认浅色主题
    
    @classmethod
    def set_theme(cls, theme: str):
        """设置当前主题"""
        if theme in ["light", "dark", "auto"]:
            cls._current_theme = theme
    
    @classmethod
    def get_current_theme(cls) -> str:
        """获取当前主题"""
        return cls._current_theme
    
    @classmethod
    def get_colors(cls):
        """根据当前主题获取颜色"""
        if cls._current_theme == "dark":
            return AntColorsDark
        else:
            return AntColors
    
    @classmethod
    def is_dark_theme(cls) -> bool:
        """判断是否为深色主题"""
        return cls._current_theme == "dark"


class MainWindowStyles:
    """主窗口样式 - Ant Design风格"""
    
    @staticmethod
    def get_rounded_window():
        colors = ThemeManager.get_colors()
        return f"""
        QWidget {{
            background-color: {colors.GRAY_1};
            border-radius: 15px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }}
    """
    
    @staticmethod
    def get_transparent_content():
        return """
        QWidget {
            background-color: transparent;
        }
    """
    
    @staticmethod
    def get_status_html_style():
        colors = ThemeManager.get_colors()
        return f"""
        <style>
            .card {{
                margin: 12px 0;
                padding: 16px;
                border-radius: 8px;
                    background-color: {colors.GRAY_1};
                    border: 1px solid {colors.GRAY_4};
            }}
            .section-title {{
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 12px;
                    color: {colors.GRAY_10};
                line-height: 1.5;
            }}
            .status-success {{
                    color: {colors.SUCCESS_6};
                font-weight: 500;
            }}
            .status-warning {{
                    color: {colors.WARNING_6};
                font-weight: 500;
            }}
            .status-error {{
                    color: {colors.ERROR_6};
                font-weight: 500;
            }}
            .status-normal {{
                    color: {colors.GRAY_8};
                font-weight: 500;
            }}
            .status-disabled {{
                    color: {colors.GRAY_6};
                font-weight: 400;
            }}
            .status-item {{
                margin: 8px 0;
                line-height: 1.5;
                font-size: 14px;
            }}
            .memory-bar {{
                height: 8px;
                    background-color: {colors.GRAY_4};
                border-radius: 4px;
                margin: 8px 0;
                position: relative;
                overflow: hidden;
            }}
            .memory-bar-fill {{
                height: 100%;
                    background-color: {colors.PRIMARY_6};
                border-radius: 4px;
            }}
            .update-time {{
                font-size: 12px;
                    color: {colors.GRAY_7};
                text-align: right;
                margin-top: 12px;
                font-style: italic;
            }}
        </style>
    """


class TitleBarStyles:
    """标题栏样式 - Ant Design风格"""
    
    @staticmethod
    def get_custom_titlebar():
        colors = ThemeManager.get_colors()
        return f"""
        CustomTitleBar {{
                background-color: {colors.GRAY_1};
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
                border-bottom: 1px solid {colors.GRAY_4};
        }}
        QLabel {{
            font-size: 14px;
            font-weight: 600;
                color: {colors.GRAY_9};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }}
    """


class TableStyles:
    """表格样式 - Ant Design Table风格"""
    
    @staticmethod
    def get_modern_table():
        colors = ThemeManager.get_colors()
        return f"""
        QTableWidget {{
                background-color: {colors.GRAY_1};
                border: 1px solid {colors.GRAY_4};
            border-radius: 6px;
                gridline-color: {colors.GRAY_4};
                selection-background-color: {colors.PRIMARY_1};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 12px;
        }}
        
        QTableWidget::item {{
            padding: 8px 12px;
            border: none;
                border-bottom: 1px solid {colors.GRAY_3};
                color: {colors.GRAY_9};
        }}
        
        QTableWidget::item:selected {{
                background-color: {colors.PRIMARY_1};
                color: {colors.PRIMARY_7};
        }}
        
        QTableWidget::item:hover {{
                background-color: {colors.GRAY_2};
        }}
        
        QTableWidget::item:alternate {{
                background-color: {colors.GRAY_2};
        }}
        
        QHeaderView::section {{
                background-color: {colors.GRAY_2};
                color: {colors.GRAY_9};
            padding: 8px 12px;
            border: none;
                border-right: 1px solid {colors.GRAY_4};
                border-bottom: 1px solid {colors.GRAY_4};
            font-weight: 600;
            font-size: 12px;
        }}
        
        QHeaderView::section:first {{
            border-top-left-radius: 6px;
        }}
        
        QHeaderView::section:last {{
            border-top-right-radius: 6px;
            border-right: none;
        }}
        
        QHeaderView::section:hover {{
                background-color: {colors.GRAY_3};
        }}
        
        QHeaderView::down-arrow {{
            image: none;
            border: none;
            width: 0px;
            height: 0px;
        }}
        
        QHeaderView::up-arrow {{
            image: none;
            border: none;
            width: 0px;
            height: 0px;
        }}
        
        QScrollBar:vertical {{
                background: {colors.GRAY_3};
            width: 8px;
            border-radius: 4px;
            margin: 0px;
        }}
        
        QScrollBar::handle:vertical {{
                background: {colors.GRAY_6};
            border-radius: 4px;
            min-height: 20px;
        }}
        
        QScrollBar::handle:vertical:hover {{
                background: {colors.GRAY_7};
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            border: none;
            background: none;
        }}
    """


class ButtonStyles:
    """按钮样式 - Ant Design Button风格"""
    
    @staticmethod
    def get_button_style(button_type="primary"):
        """获取按钮样式"""
        colors = ThemeManager.get_colors()
        
        # 预定义的按钮类型
        button_configs = {
            "primary": {
                "bg": colors.PRIMARY_6,
                "bg_hover": colors.PRIMARY_5,
                "bg_active": colors.PRIMARY_7,
                "color": colors.GRAY_1 if not ThemeManager.is_dark_theme() else colors.GRAY_13,
                "border": colors.PRIMARY_6
            },
            "default": {
                "bg": colors.GRAY_1,
                "bg_hover": colors.GRAY_2,
                "bg_active": colors.GRAY_3,
                "color": colors.GRAY_9,
                "border": colors.GRAY_5
            },
            "success": {
                "bg": colors.SUCCESS_6,
                "bg_hover": colors.SUCCESS_5,
                "bg_active": colors.SUCCESS_7,
                "color": colors.GRAY_1 if not ThemeManager.is_dark_theme() else colors.GRAY_13,
                "border": colors.SUCCESS_6
            },
            "warning": {
                "bg": colors.WARNING_6,
                "bg_hover": colors.WARNING_5,
                "bg_active": colors.WARNING_7,
                "color": colors.GRAY_1 if not ThemeManager.is_dark_theme() else colors.GRAY_13,
                "border": colors.WARNING_6
            },
            "danger": {
                "bg": colors.ERROR_6,
                "bg_hover": colors.ERROR_5,
                "bg_active": colors.ERROR_7,
                "color": colors.GRAY_1 if not ThemeManager.is_dark_theme() else colors.GRAY_13,
                "border": colors.ERROR_6
            },
            "secondary": {
                "bg": colors.GRAY_6,
                "bg_hover": colors.GRAY_5,
                "bg_active": colors.GRAY_7,
                "color": colors.GRAY_1 if not ThemeManager.is_dark_theme() else colors.GRAY_13,
                "border": colors.GRAY_6
            }
        }
        
        config = button_configs.get(button_type, button_configs["primary"])
        
        return f"""
            QPushButton {{
                background-color: {config["bg"]};
                color: {config["color"]};
                border: 1px solid {config["border"]};
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: 400;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                min-height: 28px;
                outline: none;
            }}
            
            QPushButton:hover {{
                background-color: {config["bg_hover"]};
                border-color: {config["bg_hover"]};
            }}
            
            QPushButton:pressed {{
                background-color: {config["bg_active"]};
                border-color: {config["bg_active"]};
            }}
            
            QPushButton:disabled {{
                background-color: {colors.GRAY_3};
                color: {colors.GRAY_6};
                border-color: {colors.GRAY_4};
            }}
            
            QPushButton:focus {{
                border-color: {colors.PRIMARY_6};
                border-width: 2px;
            }}
        """
    
    @staticmethod
    def get_text_button_style():
        """获取文本按钮样式"""
        colors = ThemeManager.get_colors()
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {colors.PRIMARY_6};
                border: none;
                border-radius: 4px;
                padding: 4px 6px;
                font-weight: 400;
                font-size: 12px;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            }}
            
            QPushButton:hover {{
                background-color: {colors.PRIMARY_1};
                color: {colors.PRIMARY_5};
            }}
            
            QPushButton:pressed {{
                background-color: {colors.PRIMARY_2};
                color: {colors.PRIMARY_7};
            }}
            
            QPushButton:disabled {{
                color: {colors.GRAY_6};
            }}
        """


class InputStyles:
    """输入框样式 - Ant Design Input风格"""
    
    @staticmethod
    def get_modern_input():
        colors = ThemeManager.get_colors()
        return f"""
        QLineEdit {{
                background-color: {colors.GRAY_1};
                border: 1px solid {colors.GRAY_5};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
                color: {colors.GRAY_9};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            min-height: 26px;
        }}
        
        QLineEdit:hover {{
                border-color: {colors.PRIMARY_5};
        }}
        
        QLineEdit:focus {{
                border-color: {colors.PRIMARY_6};
            outline: none;
            border-width: 2px;
        }}
        
        QLineEdit:disabled {{
                background-color: {colors.GRAY_3};
                color: {colors.GRAY_6};
                border-color: {colors.GRAY_4};
        }}
    """


class ComboBoxStyles:
    """下拉框样式 - Ant Design Select风格"""
    
    @staticmethod
    def get_modern_combo():
        colors = ThemeManager.get_colors()
        return f"""
        QComboBox {{
                background-color: {colors.GRAY_1};
                border: 1px solid {colors.GRAY_5};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
                color: {colors.GRAY_9};
            min-width: 100px;
            min-height: 26px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }}
        
        QComboBox:hover {{
                border-color: {colors.PRIMARY_5};
        }}
        
        QComboBox:focus {{
                border-color: {colors.PRIMARY_6};
            outline: none;
            border-width: 2px;
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 20px;
            padding-right: 8px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border: none;
            width: 0px;
            height: 0px;
        }}
        
        QComboBox QAbstractItemView {{
                background-color: {colors.GRAY_1};
                border: 1px solid {colors.GRAY_4};
            border-radius: 4px;
                selection-background-color: {colors.PRIMARY_1};
                selection-color: {colors.PRIMARY_7};
            padding: 2px;
            outline: none;
        }}
        
        QComboBox QAbstractItemView::item {{
            height: 26px;
            padding: 4px 8px;
            border: none;
            border-radius: 3px;
                color: {colors.GRAY_9};
        }}
        
        QComboBox QAbstractItemView::item:hover {{
                background-color: {colors.GRAY_2};
        }}
        
        QComboBox QAbstractItemView::item:selected {{
                background-color: {colors.PRIMARY_1};
                color: {colors.PRIMARY_7};
        }}
    """


class CheckBoxStyles:
    """复选框样式 - Ant Design Checkbox风格"""
    
    @staticmethod
    def get_modern_checkbox():
        colors = ThemeManager.get_colors()
        return f"""
        QCheckBox {{
            font-size: 12px;
                color: {colors.GRAY_9};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            spacing: 6px;
        }}
        
        QCheckBox::indicator {{
            width: 14px;
            height: 14px;
            border-radius: 2px;
                border: 1px solid {colors.GRAY_5};
                background-color: {colors.GRAY_1};
        }}
        
        QCheckBox::indicator:hover {{
                border-color: {colors.PRIMARY_6};
        }}
        
        QCheckBox::indicator:checked {{
                background-color: {colors.PRIMARY_6};
                border-color: {colors.PRIMARY_6};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xMC4yIDEuNEw0LjQgNy4yTDEuOCA0LjYiIHN0cm9rZT0iI0ZGRkZGRiIgc3Ryb2tlLXdpZHRoPSIxLjYiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
        }}

        QCheckBox::indicator:checked:hover {{
                background-color: {colors.PRIMARY_5};
        }}
        
        QCheckBox::indicator:disabled {{
                background-color: {colors.GRAY_3};
                border-color: {colors.GRAY_4};
        }}
    """


class RadioButtonStyles:
    """单选按钮样式 - Ant Design Radio风格"""
    
    @staticmethod
    def get_modern_radio():
        colors = ThemeManager.get_colors()
        return f"""
        QRadioButton {{
            font-size: 12px;
            color: {colors.GRAY_9};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            spacing: 6px;
        }}
        
        QRadioButton::indicator {{
            width: 14px;
            height: 14px;
            border-radius: 7px;
            border: 1px solid {colors.GRAY_5};
            background-color: {colors.GRAY_1};
        }}
        
        QRadioButton::indicator:hover {{
            border-color: {colors.PRIMARY_6};
        }}
        
        QRadioButton::indicator:checked {{
            border: 2px solid {colors.PRIMARY_6};
            background-color: {colors.GRAY_1};
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOCIgaGVpZ2h0PSI4IiB2aWV3Qm94PSIwIDAgOCA4IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxjaXJjbGUgY3g9IjQiIGN5PSI0IiByPSI0IiBmaWxsPSIjMTg5MGZmIi8+PC9zdmc+);
        }}
        
        QRadioButton::indicator:disabled {{
            background-color: {colors.GRAY_3};
            border-color: {colors.GRAY_4};
        }}
        """


class ProgressBarStyles:
    """进度条样式 - Ant Design Progress风格"""
    
    @staticmethod
    def get_modern_progress():
        colors = ThemeManager.get_colors()
        return f"""
        QProgressBar {{
            border: none;
            border-radius: 3px;
                background-color: {colors.GRAY_3};
            text-align: center;
            font-size: 11px;
                color: {colors.GRAY_8};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            max-height: 16px;
        }}
        
        QProgressBar::chunk {{
            border-radius: 3px;
                background-color: {colors.PRIMARY_6};
        }}
    """
    
    # 内存使用率进度条颜色
    @staticmethod
    def get_memory_progress_low():
        colors = ThemeManager.get_colors()
        return f"QProgressBar::chunk {{ background-color: {colors.SUCCESS_6}; }}"
    
    @staticmethod
    def get_memory_progress_medium():
        colors = ThemeManager.get_colors()
        return f"QProgressBar::chunk {{ background-color: {colors.WARNING_6}; }}"
    
    @staticmethod
    def get_memory_progress_high():
        colors = ThemeManager.get_colors()
        return f"QProgressBar::chunk {{ background-color: {colors.ERROR_6}; }}"


class GroupBoxStyles:
    """分组框样式 - Ant Design Card风格"""
    
    @staticmethod
    def get_modern_groupbox():
        colors = ThemeManager.get_colors()
        return f"""
        QGroupBox {{
            font-size: 13px;
            font-weight: 600;
                color: {colors.GRAY_9};
                background-color: {colors.GRAY_1};
                border: 1px solid {colors.GRAY_4};
            border-radius: 8px;
            margin-top: 2px;
            padding-top: 8px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top center;
            padding: 0 10px;
                background-color: {colors.GRAY_1};
                color: {colors.GRAY_9};
        }}

    """


class TabStyles:
    """选项卡样式 - Ant Design Tabs风格"""
    
    @staticmethod
    def get_modern_tabs():
        colors = ThemeManager.get_colors()
        return f"""
        QTabWidget::pane {{
                border: 1px solid {colors.GRAY_4};
            border-radius: 6px;
                background-color: {colors.GRAY_1};
            margin-top: -1px;
        }}
        
        QTabBar::tab {{
                background-color: {colors.GRAY_2};
                color: {colors.GRAY_8};
            padding: 6px 12px;
            margin-right: 1px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
                border: 1px solid {colors.GRAY_4};
            border-bottom: none;
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            min-width: 70px;
        }}
        
        QTabBar::tab:selected {{
                background-color: {colors.GRAY_1};
                color: {colors.PRIMARY_6};
                border-color: {colors.GRAY_4};
                border-bottom-color: {colors.GRAY_1};
        }}
        
        QTabBar::tab:hover:!selected {{
                background-color: {colors.GRAY_3};
                color: {colors.GRAY_9};
        }}
    """


class LabelStyles:
    """标签样式 - Ant Design Typography风格"""
    
    @staticmethod
    def get_modern_label():
        colors = ThemeManager.get_colors()
        return f"""
        QLabel {{
                color: {colors.GRAY_9};
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.4;
        }}
    """
    
    @staticmethod
    def get_info_hint():
        colors = ThemeManager.get_colors()
        return f"""
        QLabel {{
                color: {colors.GRAY_7};
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.4;
            padding: 6px 8px;
                background-color: {colors.GRAY_2};
                border: 1px solid {colors.GRAY_4};
            border-radius: 4px;
            margin: 3px 0;
        }}
    """
    
    @staticmethod
    def get_success_hint():
        colors = ThemeManager.get_colors()
        return f"""
        QLabel {{
                color: {colors.SUCCESS_7};
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.4;
            padding: 6px 8px;
                background-color: {colors.SUCCESS_1};
                border: 1px solid {colors.SUCCESS_3};
            border-radius: 4px;
            margin: 3px 0;
        }}
    """
    
    @staticmethod
    def get_warning_hint():
        colors = ThemeManager.get_colors()
        return f"""
        QLabel {{
                color: {colors.WARNING_7};
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.4;
            padding: 6px 8px;
                background-color: {colors.WARNING_1};
                border: 1px solid {colors.WARNING_3};
            border-radius: 4px;
            margin: 3px 0;
        }}
    """
    
    @staticmethod
    def get_error_hint():
        colors = ThemeManager.get_colors()
        return f"""
        QLabel {{
                color: {colors.ERROR_7};
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.4;
            padding: 6px 8px;
                background-color: {colors.ERROR_1};
                border: 1px solid {colors.ERROR_3};
            border-radius: 4px;
            margin: 3px 0;
        }}
    """
    
    @staticmethod
    def get_secondary_text():
        colors = ThemeManager.get_colors()
        return f"""
        QLabel {{
                color: {colors.GRAY_7};
            font-size: 12px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.4;
        }}
    """
    
    @staticmethod
    def get_small_text():
        colors = ThemeManager.get_colors()
        return f"""
        QLabel {{
                color: {colors.GRAY_8};
            font-size: 10px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.3;
        }}
    """


class SpinBoxStyles:
    """数字输入框样式 - Ant Design InputNumber风格"""
    
    @staticmethod
    def get_modern_spinbox():
        colors = ThemeManager.get_colors()
        return f"""
        QSpinBox {{
                background-color: {colors.GRAY_1};
                border: 1px solid {colors.GRAY_5};
            border-radius: 4px;
            padding: 4px 8px;
            font-size: 12px;
                color: {colors.GRAY_9};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            min-height: 26px;
        }}
        
        QSpinBox:hover {{
                border-color: {colors.PRIMARY_5};
        }}
        
        QSpinBox:focus {{
                border-color: {colors.PRIMARY_6};
            outline: none;
            border-width: 2px;
        }}
        
        QSpinBox::up-button, QSpinBox::down-button {{
            border: none;
            width: 16px;
            background-color: transparent;
        }}
        
        QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
                background-color: {colors.GRAY_2};
        }}
    """


class ColorScheme:
    """颜色方案 - Ant Design颜色系统"""
    
    @staticmethod
    def get_colors():
        """获取当前主题的颜色"""
        return ThemeManager.get_colors()
    
    @classmethod
    def SUCCESS(cls):
        return cls.get_colors().SUCCESS_6
    
    @classmethod
    def WARNING(cls):
        return cls.get_colors().WARNING_6
    
    @classmethod
    def ERROR(cls):
        return cls.get_colors().ERROR_6
    
    @classmethod
    def NORMAL(cls):
        return cls.get_colors().GRAY_9
    
    @classmethod
    def DISABLED(cls):
        return cls.get_colors().GRAY_6
    
    @classmethod
    def INFO(cls):
        return cls.get_colors().PRIMARY_6
    
    @classmethod
    def PRIMARY(cls):
        return cls.get_colors().PRIMARY_6
    
    @classmethod
    def SUCCESS_BTN(cls):
        return cls.get_colors().SUCCESS_6
    
    @classmethod
    def DANGER(cls):
        return cls.get_colors().ERROR_6
    
    @classmethod
    def WARNING_BTN(cls):
        return cls.get_colors().WARNING_6
    
    @classmethod
    def SECONDARY(cls):
        return cls.get_colors().GRAY_6
    
    @classmethod
    def MEMORY_LOW(cls):
        return cls.get_colors().SUCCESS_6
    
    @classmethod
    def MEMORY_MEDIUM(cls):
        return cls.get_colors().WARNING_6
    
    @classmethod
    def MEMORY_HIGH(cls):
        return cls.get_colors().ERROR_6
    
    @classmethod
    def PROCESS_RUNNING(cls):
        return cls.get_colors().SUCCESS_6
    
    @classmethod
    def PROCESS_SYSTEM(cls):
        return cls.get_colors().GRAY_7
    
    @classmethod
    def PROCESS_USER(cls):
        return cls.get_colors().GRAY_9
    
    @classmethod
    def PROCESS_SYSTEM_USER(cls):
        return cls.get_colors().ERROR_6
    
    @classmethod
    def TEXT_PRIMARY(cls):
        return cls.get_colors().GRAY_9
    
    @classmethod
    def TEXT_SECONDARY(cls):
        return cls.get_colors().GRAY_7
    
    @classmethod
    def TEXT_DISABLED(cls):
        return cls.get_colors().GRAY_6
    
    @classmethod
    def BG_PRIMARY(cls):
        return cls.get_colors().GRAY_1
    
    @classmethod
    def BG_SECONDARY(cls):
        return cls.get_colors().GRAY_2
    
    @classmethod
    def BG_DISABLED(cls):
        return cls.get_colors().GRAY_3
    
    @classmethod
    def BORDER_PRIMARY(cls):
        return cls.get_colors().GRAY_5
    
    @classmethod
    def BORDER_SECONDARY(cls):
        return cls.get_colors().GRAY_4
    
    @classmethod
    def BORDER_LIGHT(cls):
        return cls.get_colors().GRAY_3


# 全局样式应用器
class StyleApplier:
    """样式应用器"""
    
    @staticmethod
    def apply_ant_design_theme(app):
        """应用Ant Design主题到整个应用"""
        colors = ThemeManager.get_colors()
        
        global_style = f"""
            * {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            }}
            
            QWidget {{
                background-color: {colors.GRAY_1};
                color: {colors.GRAY_9};
            }}
            
            QLabel {{
                color: {colors.GRAY_9};
                font-size: 14px;
            }}
            
            QMessageBox {{
                background-color: {colors.GRAY_1};
                border: 1px solid {colors.GRAY_4};
                border-radius: 8px;
            }}
            
            QMenuBar {{
                background-color: {colors.GRAY_1};
                border-bottom: 1px solid {colors.GRAY_4};
                color: {colors.GRAY_9};
            }}
            
            QMenu {{
                background-color: {colors.GRAY_1};
                border: 1px solid {colors.GRAY_4};
                border-radius: 6px;
                padding: 4px;
            }}
            
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 4px;
            }}
            
            QMenu::item:selected {{
                background-color: {colors.PRIMARY_1};
                color: {colors.PRIMARY_7};
            }}
            
            QRadioButton {{
                color: {colors.GRAY_9};
                background-color: transparent;
            }}
            
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 1px solid {colors.GRAY_5};
                background-color: {colors.GRAY_1};
            }}
            
            QRadioButton::indicator:hover {{
                border-color: {colors.PRIMARY_6};
            }}
            
            QRadioButton::indicator:checked {{· 
                border: 2px solid {colors.PRIMARY_6};
                background-color: {colors.GRAY_1};
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iOCIgaGVpZ2h0PSI4IiB2aWV3Qm94PSIwIDAgOCA4IiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPjxjaXJjbGUgY3g9IjQiIGN5PSI0IiByPSI0IiBmaWxsPSIjMTg5MGZmIi8+PC9zdmc+);
            }}
            
            QToolTip {{
                background-color: {colors.GRAY_10};
                color: {colors.GRAY_1};
                border: 1px solid {colors.GRAY_8};
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }}
        """
        
        app.setStyleSheet(global_style)