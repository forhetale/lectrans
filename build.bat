@echo off
echo.
echo ==========================================
echo    LecTrans Build Tool v5
echo    Azure Speech + MiMo
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install openai azure-cognitiveservices-speech pyaudio pyinstaller -q
echo.

echo [2/3] Building exe...
python -m PyInstaller --onefile --windowed --name LecTrans ^
    --hidden-import openai ^
    --hidden-import openai._client ^
    --hidden-import openai.resources ^
    --hidden-import openai.resources.chat ^
    --hidden-import openai.resources.chat.completions ^
    --hidden-import azure.cognitiveservices.speech ^
    --hidden-import pyaudio ^
    --hidden-import pyaudio._portaudio ^
    --hidden-import httpx ^
    --hidden-import pydantic ^
    --hidden-import pydantic_core ^
    --hidden-import anyio ^
    --hidden-import sniffio ^
    --hidden-import distro ^
    --hidden-import jiter ^
    --hidden-import h11 ^
    --hidden-import tkinter ^
    --hidden-import tkinter.ttk ^
    --exclude-module numpy ^
    --exclude-module pandas ^
    --exclude-module matplotlib ^
    --exclude-module PIL ^
    --exclude-module groq ^
    lectrans_gui_v4.py

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
if exist build rd /s /q build >nul 2>&1
if exist lectrans_gui_v4.spec del /q lectrans_gui_v4.spec >nul 2>&1

echo.
echo ==========================================
echo    Success! File: dist\LecTrans.exe
echo ==========================================
echo.
pause