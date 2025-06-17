<div align="center">

# ACE-KILLER

<img src="https://github.com/Cassianvale/ACE-KILLER/raw/main/assets/icon/favicon.ico" width="120px" alt="ACE-KILLER Logo"/>

✨ **游戏反作弊进程管理工具，专为无畏契约、三角洲行动等使用 ACE 反作弊的游戏设计** ✨

<div>
<img alt="platform" src="https://img.shields.io/badge/platform-Windows-blueviolet">
<img alt="python" src="https://img.shields.io/badge/Python-3.10+-blue.svg">
<img alt="license" src="https://img.shields.io/badge/License-GPL--3.0-green.svg">
<img alt="version" src="https://img.shields.io/github/v/release/Cassianvale/ACE-KILLER?color=orange&label=Version">
</div>

<div>
    <a href="https://github.com/Cassianvale/ACE-KILLER"><img alt="stars" src="https://img.shields.io/github/stars/Cassianvale/ACE-KILLER?style=social"></a>
    <a href="https://github.com/Cassianvale/ACE-KILLER/releases/latest"><img alt="downloads" src="https://img.shields.io/github/downloads/Cassianvale/ACE-KILLER/total?style=social"></a>
</div>

<br/>

> 项目设计初衷并非直接对抗反作弊程序，不涉及对反作弊内核的修改，所以不用担心会封号问题  
> 本工具对`SGuard64.exe`扫盘进程进行了限制，减少帧数波动，将反作弊服务的管理权交还给玩家

</div>

## ✅ 功能特性

- 🛡️ 自动关闭`ACE-Tray.exe`反作弊安装询问弹窗
- 🚀 自动优化`SGuard64.exe`扫盘进程，降低 CPU 占用
- 🗑️ 支持一键启动/停止反作弊进程，卸载/删除 ACE 反作弊服务
- 🐻 支持自定义进程性能模式
- 🧹 内存清理根据作者`H3d9`编写的 [Memory Cleaner](https://github.com/H3d9/memory_cleaner) 进行重构
- 📱 支持 Windows 系统通知
- 🔄 支持开机静默自启
- 💻 系统托盘常驻运行
- 🌓 支持明暗主题切换

## 🚀 如何使用

1. 下载最新版本的[发布包](https://github.com/Cassianvale/ACE-KILLER/releases)
2. 解压后运行`ACE-KILLER.exe`
3. 程序将在系统托盘显示图标
4. 右键点击托盘图标可以：
   - 👁️ 查看程序状态
   - 🔔 启用/禁用 Windows 通知
   - 🔄 设置开机自启动
   - ⚙️ 配置游戏监控
   - 📁 打开配置目录
   - 🚪 退出程序

## 项目展示

<div align="center">
  <img src="https://raw.githubusercontent.com/Cassianvale/ACE-KILLER/main/assets/image/1.png" width="45%" alt="应用界面预览">
  <img src="https://raw.githubusercontent.com/Cassianvale/ACE-KILLER/main/assets/image/2.png" width="45%" alt="进程监控界面预览1">
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/Cassianvale/ACE-KILLER/main/assets/image/3.png" width="45%" alt="内存清理界面预览">
  <img src="https://raw.githubusercontent.com/Cassianvale/ACE-KILLER/main/assets/image/4.png" width="45%" alt="设置界面预览">
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/Cassianvale/ACE-KILLER/main/assets/image/5.png" width="80%" alt="进程监控界面预览2">
</div>

## 进程模式策略

| 性能模式    | CPU 优先级             | 效能节流     | CPU 亲和性   |
| ----------- | ---------------------- | ------------ | ------------ |
| 🌱 效能模式 | 低优先级(IDLE)         | 启用节流     | 最后一个核心 |
| 🍉 正常模式 | **正常优先级(NORMAL)** | **禁用节流** | 所有核心     |
| 🚀 高性能   | 高优先级(HIGH)         | 禁用节流     | 所有核心     |
| 🔥 最大性能 | 实时优先级(REALTIME)   | 禁用节流     | 所有核心     |

## ⚙️ ACE Services 说明

- **AntiCheatExpert Service**：用户模式，由 `SvGuard64.exe` 控制的游戏交互的服务，也是在服务概览 (services.msc) 中看到的唯一服务
- **AntiCheatExpert Protection**：反作弊组件
- **ACE-BASE**：内核模式，加载系统驱动程序
- **ACE-GAME**：内核模式，加载系统驱动程序

## ⚠️ 注意事项

- 本程序需要管理员权限运行
- 使用过程中如遇到问题，日志文件位于 `%USERPROFILE%\.ace-killer\logs\` 目录

## 📢 免责声明

- **本项目仅供个人学习和研究使用，禁止用于任何商业或非法目的。**
- **开发者保留对本项目的最终解释权。**
- **使用者在使用本项目时，必须严格遵守 `中华人民共和国（含台湾省）` 以及使用者所在地区的法律法规。禁止将本项目用于任何违反相关法律法规的活动。**
- **使用者应自行承担因使用本项目所产生的任何风险和责任。开发者不对因使用本项目而导致的任何直接或间接损失承担责任。**
- **开发者不对本项目所提供的服务或内容的准确性、完整性或适用性作出任何明示或暗示的保证。使用者应自行评估使用本项目的风险。**
- **若使用者发现任何商家或第三方以本项目进行收费或从事其他商业行为，所产生的任何问题或后果与本项目及开发者无关。使用者应自行承担相关风险。**

## 📜 许可证

- **本项目采用 `GNU General Public License v3.0`** - 详见 [LICENSE](LICENSE) 文件
