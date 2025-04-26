<div align="center">

# ACE-KILLER

<img src="https://github.com/Cassianvale/ACE-KILLER/raw/main/assets/icon/favicon.ico" width="120px" alt="ACE-KILLER Logo"/>

✨ **游戏反作弊进程管理工具，专为无畏契约、三角洲行动等使用ACE反作弊的游戏设计** ✨

<div>
<img alt="platform" src="https://img.shields.io/badge/platform-Windows-blueviolet">
<img alt="python" src="https://img.shields.io/badge/Python-3.10+-blue.svg">
<img alt="license" src="https://img.shields.io/badge/License-GPL--3.0-green.svg">
<img alt="version" src="https://img.shields.io/badge/Version-1.0.2-orange.svg">
</div>

<div>
    <a href="https://github.com/Cassianvale/ACE-KILLER"><img alt="stars" src="https://img.shields.io/github/stars/Cassianvale/ACE-KILLER?style=social"></a>
    <a href="https://github.com/Cassianvale/ACE-KILLER/releases/latest"><img alt="downloads" src="https://img.shields.io/github/downloads/Cassianvale/ACE-KILLER/total?style=social"></a>
</div>

<br/>

> 项目设计初衷并非直接对抗反作弊程序，而是优化扫盘程序对系统资源的占用优化1%low帧，并且能让用户能更好的对反作弊程序进行管理

</div>

## ✅ 功能特性

- 🛡️ 自动关闭`ACE-Tray.exe`反作弊进程询问弹窗(拒绝也没用，进游戏会默认加载)
- 🚀 优化`SGuard64.exe`扫描进程，降低CPU占用
- 🎮 支持自定义同时监控多个TX游戏
- 📱 支持Windows系统通知
- 🔄 支持开机自启动
- 💻 系统托盘常驻运行
- 🧹 内存清理根据`H3d9`大佬C++编写的 [Memory Cleaner](https://github.com/H3d9/memory_cleaner) 重构而来
- 🌓 支持明暗主题切换
- 🗑️ 支持一键卸载ACE反作弊服务

## 项目展示

<div align="center">
  <img src="https://github.com/Cassianvale/ACE-KILLER/raw/main/assets/image/app_1.png" width="60%" alt="应用界面预览">
  <p>ACE-KILLER 应用界面</p>
</div>
<div align="center">
  <img src="https://github.com/Cassianvale/ACE-KILLER/raw/main/assets/image/app_3.png" width="60%" alt="内存清理界面预览">
  <p>ACE-KILLER 内存清理界面</p>
</div>
<div align="center">
  <img src="https://github.com/Cassianvale/ACE-KILLER/raw/main/assets/image/app_4.png" width="60%" alt="设置界面预览">
  <p>ACE-KILLER 设置界面</p>
</div>


## 📂 项目结构

| 文件/目录 | 描述 |
| --- | --- |
| `main.py` | 程序入口文件 |
| `core/process_monitor.py` | 进程监控核心实现 |
| `core/system_utils.py` | 系统工具函数 |
| `config/config_manager.py` | 配置管理器 |
| `ui/tray_icon.py` | 系统托盘界面 |
| `utils/logger.py` | 日志工具 |
| `utils/notification.py` | 通知系统 |
| `models/game_config.py` | 游戏配置数据模型 |
| `requirements.txt` | 项目依赖列表 |

## 💻 技术栈

<table>
  <tr>
    <td><b>核心技术</b></td>
    <td>Python 3.10+</td>
  </tr>
  <tr>
    <td><b>界面框架</b></td>
    <td>PySide6, pyqtdarktheme</td>
  </tr>
  <tr>
    <td><b>系统交互</b></td>
    <td>psutil, PyWin32</td>
  </tr>
  <tr>
    <td><b>辅助工具</b></td>
    <td>loguru, win11toast, PyYAML</td>
  </tr>
</table>

## 🚀 如何使用

1. 下载最新版本的[发布包](https://github.com/Cassianvale/ACE-KILLER/releases)
2. 解压后运行`ACE-KILLER.exe`
3. 程序将在系统托盘显示图标
4. 右键点击托盘图标可以：
   - 👁️ 查看程序状态
   - 🔔 启用/禁用Windows通知
   - 🔄 设置开机自启动
   - ⚙️ 配置游戏监控
   - 📁 打开配置目录
   - 🚪 退出程序

## ⚙️ ACE Control 说明

- **AntiCheatExpert Service**：用户模式，由 `SvGuard64.exe` 控制的游戏交互的服务，也是在服务概览 (services.msc) 中看到的唯一服务
- **AntiCheatExpert Protection**：反作弊组件
- **ACE-BASE**：内核模式，加载系统驱动程序
- **ACE-GAME**：内核模式，加载系统驱动程序

## ⚠️ 注意事项

- 本程序需要管理员权限运行
- 使用过程中如遇到问题，日志文件位于 `%USERPROFILE%\.ace-killer\logs\` 目录

## 📜 许可证

本项目采用 GNU General Public License v3.0 - 详见 [LICENSE](LICENSE) 文件

