# ACE-KILLER

游戏反作弊进程管理工具，专为无畏契约、三角洲行动等使用ACE反作弊的游戏设计。

## 功能特性

- 自动终止ACE-Tray.exe反作弊进程
- 优化SGuard64.exe扫描进程，降低CPU占用
- 支持多游戏同时监控
- 支持Windows系统通知
- 支持开机自启动
- 系统托盘常驻运行

## 项目结构

```
ace_killer/
├── __init__.py               # 项目初始化文件
├── main.py                   # 程序入口
├── models/                   # 数据模型
│   ├── __init__.py
│   └── game_config.py        # 游戏配置类
├── core/                     # 核心功能
│   ├── __init__.py
│   ├── process_monitor.py    # 进程监控
│   └── system_utils.py       # 系统工具函数
├── config/                   # 配置管理
│   ├── __init__.py
│   └── config_manager.py     # 配置管理器
├── utils/                    # 工具函数
│   ├── __init__.py
│   ├── logger.py             # 日志工具
│   └── notification.py       # 通知系统
└── ui/                       # 用户界面
    ├── __init__.py
    └── tray_icon.py          # 系统托盘
```

## 技术栈

- Python 3.10+
- psutil：进程管理
- PyWin32：Windows API调用
- loguru：日志系统
- pystray：系统托盘
- win11toast：通知系统
- PyYAML：配置文件管理

## 如何使用

1. 下载最新版本的发布包
2. 解压后运行ACE-KILLER.exe
3. 程序将在系统托盘显示图标
4. 右键点击托盘图标可以：
   - 查看程序状态
   - 启用/禁用Windows通知
   - 设置开机自启动
   - 配置游戏监控
   - 打开配置目录
   - 退出程序

## 自定义配置

配置文件位于`%USERPROFILE%\.ace-killer\config.yaml`，可以手动编辑添加游戏配置：

```yaml
games:
  - name: 游戏名称
    launcher: 启动器进程名.exe
    main_game: 主游戏进程名.exe
    enabled: true/false
```

## ACE Control
“AntiCheatExpert Service”：用户模式，由 SvGuard64.exe 控制，这是游戏交互的服务，也是在服务概览 (services.msc) 中看到的唯一服务
“ACE-BASE”：内核模式，加载系统驱动程序
“ACE-GAME”：内核模式，加载系统驱动程序

sc delete ACE-GAME
sc delete ACE-BASE
sc delete "AntiCheatExpert Service"
sc delete "AntiCheatExpert Protection"

## 注意事项

- 本程序需要管理员权限运行
- 使用过程中如遇到问题，日志文件位于`%USERPROFILE%\.ace-killer\logs\`目录

