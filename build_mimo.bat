@echo off
chcp 65001 >nul
echo.
echo ==========================================
echo    LecTrans - Windows 打包工具
echo    全部使用小米 MiMo API
echo ==========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python
    echo 请先安装 Python 3.9+：https://www.python.org/downloads/
    echo 安装时请勾选 "Add Python to PATH"
    pause
    exit /b 1
)

echo [1/5] 检查 Python 版本...
python --version
echo.

echo [2/5] 安装依赖...
pip install openai httpx pydantic python-dotenv pyinstaller --quiet
echo.

echo [3/5] 开始打包...
echo 这可能需要几分钟，请耐心等待...
echo.

pyinstaller --onefile --windowed --name LecTrans ^
    --hidden-import openai ^
    --hidden-import openai._client ^
    --hidden-import openai.resources ^
    --hidden-import openai.resources.chat ^
    --hidden-import openai.resources.chat.completions ^
    --hidden-import openai.resources.audio ^
    --hidden-import openai.resources.audio.transcriptions ^
    --hidden-import httpx ^
    --hidden-import httpx._client ^
    --hidden-import pydantic ^
    --hidden-import pydantic_core ^
    --hidden-import anyio ^
    --hidden-import sniffio ^
    --hidden-import distro ^
    --hidden-import jiter ^
    --hidden-import h11 ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --hidden-import tkinter.messagebox ^
    --hidden-import tkinter.filedialog ^
    --exclude-module tkinter.test ^
    --exclude-module unittest ^
    --exclude-module pytest ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    --exclude-module scipy ^
    --exclude-module sklearn ^
    --exclude-module groq ^
    lectrans_mimo.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！
    echo 请检查错误信息并重试
    pause
    exit /b 1
)

echo.
echo [4/5] 清理临时文件...
if exist build rd /s /q build >nul 2>&1
if exist lectrans_mimo.spec del /q lectrans_mimo.spec >nul 2>&1

echo.
echo [5/5] 完成！
echo.
echo ==========================================
echo    打包成功！
echo ==========================================
echo.
echo    文件位置: dist\LecTrans.exe
echo.
echo    使用方法:
echo    1. 复制 dist\LecTrans.exe 到任意位置
echo    2. 双击运行
echo    3. 点击"设置"配置 MiMo API Key
echo    4. 点击"开始录音"使用
echo.
echo    MiMo API 获取地址:
echo    https://mimo.xiaomi.com
echo.
echo    功能说明:
echo    - 语音识别: MiMo-V2.5-ASR
echo    - 翻译/总结: MiMo-V2.5-Pro
echo    - 全部使用同一个 API Key
echo.
pause
