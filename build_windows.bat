@echo off
REM LecTrans Windows 打包脚本
REM 需要先安装 Python 3.9+ 和 pip

echo ==========================================
echo LecTrans - Windows 打包脚本
echo ==========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.9+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 安装依赖
echo [1/4] 安装依赖...
pip install -r requirements.txt pyinstaller --quiet

REM 打包
echo [2/4] 打包应用...
pyinstaller --onefile --windowed --name LecTrans ^
    --hidden-import openai ^
    --hidden-import groq ^
    --hidden-import httpx ^
    --hidden-import pydantic ^
    --hidden-import pydantic_core ^
    --hidden-import anyio ^
    --hidden-import sniffio ^
    --hidden-import distro ^
    --hidden-import jiter ^
    --hidden-import h11 ^
    --exclude-module tkinter.test ^
    --exclude-module unittest ^
    --exclude-module pytest ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    gui_app.py

REM 完成
echo.
echo [3/4] 打包完成！
echo.
echo 可执行文件位置: dist\LecTrans.exe
echo.
echo [4/4] 清理临时文件...
rd /s /q build >nul 2>&1
del /q *.spec >nul 2>&1

echo.
echo ==========================================
echo 打包完成！
echo ==========================================
echo.
echo 文件位置: dist\LecTrans.exe
echo.
echo 使用方法:
echo 1. 复制 dist\LecTrans.exe 到任意位置
echo 2. 双击运行
echo 3. 在设置中配置 API Key
echo.
pause
