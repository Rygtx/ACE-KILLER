import os
import sys
import subprocess
import shutil

# 获取当前脚本所在目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 设置图标文件路径
icon_path = os.path.join(current_dir, 'favicon.ico')

# 确保nuitka已安装
try:
    import nuitka
except ImportError:
    print("正在安装Nuitka打包工具...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka"])

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
    # 优化选项
    "--lto=yes",  # 链接时优化
    "--mingw64",  # 使用MinGW64
    "--jobs=4",  # 使用多核编译加速
    "--show-memory",  # 显示内存使用情况
    "--disable-cache=all",  # 禁用缓存
    "--clean-cache=all",  # 清除现有缓存
    "--show-progress",  # 显示编译进度
    "--output-filename=VALORANT_ACE_KILL.exe",  # 指定输出文件名
    "--nofollow-import-to=tkinter,PIL.ImageTk",  # 不跟随部分不必要模块
    "--prefer-source-code",  # 优先使用源代码而不是字节码
    "--python-flag=no_site",  # 不导入site
    "--python-flag=no_warnings",  # 不显示警告
    "--low-memory",  # 低内存使用模式
    "main.py"  # 主脚本
]

print("🚀 开始使用Nuitka打包...")
print("⏱️ 打包过程可能需要几分钟，请耐心等待...")

# 执行打包命令
try:
    subprocess.check_call(cmd)
    
    # 查找生成的可执行文件
    dist_dir = os.path.join(current_dir, "main.dist")
    final_exe = os.path.join(current_dir, "VALORANT_ACE_KILL.exe")
    
    # 首先尝试直接查找VALORANT_ACE_KILL.exe
    for root, dirs, files in os.walk(dist_dir):
        if "VALORANT_ACE_KILL.exe" in files:
            found_exe = os.path.join(root, "VALORANT_ACE_KILL.exe")
            break
    
    # 如果没找到，则查找main.exe并重命名
    if not found_exe:
        main_exe_path = os.path.join(dist_dir, "main.dist", "main.exe")
        if os.path.exists(main_exe_path):
            found_exe = main_exe_path
            
            # 在main.dist目录中创建一个VALORANT_ACE_KILL.exe的副本
            dist_valorant_exe = os.path.join(os.path.dirname(main_exe_path), "VALORANT_ACE_KILL.exe")
            shutil.copy2(main_exe_path, dist_valorant_exe)
            print(f"✅ 打包成功！可执行文件已生成: {(dist_valorant_exe)}")
        
        # 输出文件大小信息
        size_mb = os.path.getsize(dist_valorant_exe) / (1024 * 1024)
        print(f"📦 可执行文件大小: {size_mb:.2f} MB")
    else:
        print("❌ 打包完成，但未找到生成的可执行文件")
        
except subprocess.CalledProcessError as e:
    print(f"❌ 打包失败: {e}")
    sys.exit(1)

print("✅ VALORANT ACE KILLER 使用Nuitka打包完成！")
