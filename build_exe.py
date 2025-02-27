import PyInstaller.__main__
import os
import sys

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 设置图标文件路径（如果有的话）
icon_path = os.path.join(current_dir, 'favicon.ico')

# 设置打包参数
args = [
    'main.py',  # 主脚本
    '--name=VALORANT_ACE_KILL',  # 输出的EXE名称
    '--noconsole',  # 不显示控制台窗口
    '--clean',  # 清理临时文件
    '--onefile',  # 打包成单个EXE文件
    f'--icon={icon_path}',  # 设置图标（如果有）
    '--hidden-import=win32timezone',  # 解决可能的导入问题
    '--hidden-import=PIL._tkinter_finder',  # 解决PIL相关导入问题
    '--uac-admin',  # 请求管理员权限
]

# 运行PyInstaller
PyInstaller.__main__.run(args)

print("打包完成！EXE文件位于dist目录中。")
