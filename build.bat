@echo off
echo.
echo ==========================================
echo    LecTrans Build Tool v7
echo    (faster-whisper / Azure Speech + MiMo)
echo ==========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
python -m pip install -r requirements.txt pyinstaller -q
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo.

echo [2/3] Building exe from LecTrans.spec...
python -m PyInstaller LecTrans.spec --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [3/3] Done!
echo.
echo ==========================================
echo    Success! File: dist\LecTrans.exe
echo    Note: exe uses Azure ASR; for local
echo    Whisper run from source (see BUILD_GUIDE.md)
echo ==========================================
echo.
pause
