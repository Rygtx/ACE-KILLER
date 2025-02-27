@echo off
echo 正在安装必要的依赖...
pip install -r requirements.txt
echo 依赖安装完成，开始打包EXE...
python build_exe.py
echo 打包完成！
echo EXE文件位于dist目录中。
pause
