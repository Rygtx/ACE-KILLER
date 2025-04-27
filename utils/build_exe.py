import os
import sys
import subprocess
import shutil

# 设置标准输出编码为UTF-8，解决Windows环境下中文输出问题
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python 3.6及更早版本兼容
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 获取项目根目录
root_dir = os.path.dirname(current_dir)

# 设置图标文件路径
icon_path = os.path.join(root_dir, 'assets', 'icon', 'favicon.ico')

# 确保nuitka已安装
try:
    import nuitka
except ImportError:
    print("Installing Nuitka...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka"])

# PySide6相关设置
try:
    from PySide6.QtCore import QLibraryInfo
    qt_plugins_path = QLibraryInfo.path(QLibraryInfo.PluginsPath)
    qt_translations_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    qt_binaries_path = QLibraryInfo.path(QLibraryInfo.BinariesPath)
    print(f"[OK] Qt plugins path found: {qt_plugins_path}")
except ImportError:
    print("[ERROR] Cannot import PySide6, please make sure it is installed")
    sys.exit(1)

# 构建Nuitka打包命令
cmd = [
    sys.executable,
    "-m", "nuitka",
    "--standalone",  # 生成独立可执行文件
    "--windows-console-mode=disable",  # 禁用控制台
    "--windows-icon-from-ico=" + icon_path,  # 设置图标
    "--include-data-files=%s=favicon.ico" % icon_path,  # 添加图标文件
    "--windows-uac-admin",  # 请求管理员权限
    "--remove-output",  # 在重新构建前移除输出目录
    
    # PySide6 相关配置
    "--enable-plugin=pyside6",  # 启用PySide6插件

    # 优化选项
    "--lto=yes",  # 链接时优化
    "--mingw64",  # 使用MinGW64
    "--jobs=4",  # 使用多核编译加速
    "--show-memory",  # 显示内存使用情况
    "--disable-cache=all",  # 禁用缓存
    "--clean-cache=all",  # 清除现有缓存
    "--show-progress",  # 显示编译进度
    "--output-filename=ACE-KILLER.exe",  # 指定输出文件名
    "--nofollow-import-to=tkinter,PIL.ImageTk",  # 不跟随部分不必要模块
    "--prefer-source-code",  # 优先使用源代码而不是字节码
    "--python-flag=no_site",  # 不导入site
    "--python-flag=no_warnings",  # 不显示警告
    "--low-memory",  # 低内存使用模式
    "main.py"
]

print("[START] Starting Nuitka packaging...")
print("[INFO] Packaging process may take a few minutes, please be patient...")

# 执行打包命令
try:
    # 切换到项目根目录执行打包命令
    os.chdir(root_dir)
    subprocess.check_call(cmd)
    
    # 查找生成的可执行文件
    main_exe = os.path.join(root_dir, "main.dist", "ACE-KILLER.exe")
    
    # 首先判断main_exe是否存在
    if os.path.exists(main_exe):
        print(f"[SUCCESS] Packaging successful! Executable generated: {(main_exe)}")
        
        # 输出文件大小信息
        size_mb = os.path.getsize(main_exe) / (1024 * 1024)
        print(f"[INFO] Executable size: {size_mb:.2f} MB")
    else:
        print("[ERROR] Packaging complete, but executable file not found")
        
except subprocess.CalledProcessError as e:
    print(f"[ERROR] Packaging failed: {e}")
    sys.exit(1)

# 压缩可执行文件目录
dist_dir = os.path.join(root_dir, "main.dist")
zip_name = "ACE-KILLER-v1.0.0-x64"
zip_path = os.path.join(root_dir, zip_name + ".zip")
if os.path.exists(dist_dir):
    print("[INFO] Compressing executable directory...")
    # 确保在正确的位置创建zip文件
    shutil.make_archive(os.path.join(root_dir, zip_name), 'zip', dist_dir)
    print(f"[SUCCESS] Compression complete! Generated zip file: {zip_path}")
else:
    print("[ERROR] Executable directory not found, cannot compress.")
    sys.exit(1)

print("[SUCCESS] ACE-KILLER Nuitka packaging and compression completed!")
