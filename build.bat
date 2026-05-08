@echo off
echo.
echo ==========================================
echo    LecTrans Build Tool v6
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

REM 获取 Azure Speech SDK 路径
for /f "tokens=*" %%i in ('python -c "import azure.cognitiveservices.speech; import os; print(os.path.dirname(azure.cognitiveservices.speech.__file__))"') do set AZURE_SDK_PATH=%%i

echo Azure SDK Path: %AZURE_SDK_PATH%

python -m PyInstaller --onefile --windowed --name LecTrans ^
    --add-binary "%AZURE_SDK_PATH%\Microsoft.CognitiveServices.Speech.core.dll;azure\cognitiveservices\speech" ^
    --add-binary "%AZURE_SDK_PATH%\Microsoft.CognitiveServices.Speech.extension.audio.sys.dll;azure\cognitiveservices\speech" ^
    --add-binary "%AZURE_SDK_PATH%\Microsoft.CognitiveServices.Speech.extension.codec.dll;azure\cognitiveservices\speech" ^
    --add-binary "%AZURE_SDK_PATH%\Microsoft.CognitiveServices.Speech.extension.kws.dll;azure\cognitiveservices\speech" ^
    --add-binary "%AZURE_SDK_PATH%\Microsoft.CognitiveServices.Speech.extension.kws.ort.dll;azure\cognitiveservices\speech" ^
    --hidden-import openai ^
    --hidden-import openai._client ^
    --hidden-import openai._base_client ^
    --hidden-import openai._exceptions ^
    --hidden-import openai._models ^
    --hidden-import openai._qs ^
    --hidden-import openai._utils ^
    --hidden-import openai.lib ^
    --hidden-import openai.lib._parsing ^
    --hidden-import openai.lib._completers ^
    --hidden-import openai.lib._responses ^
    --hidden-import openai.lib._streaming ^
    --hidden-import openai.lib._tool_converters ^
    --hidden-import openai.lib._pydantic ^
    --hidden-import openai.resources ^
    --hidden-import openai.resources.audio ^
    --hidden-import openai.resources.chat ^
    --hidden-import openai.resources.chat.completions ^
    --hidden-import openai.resources.audio.transcriptions ^
    --hidden-import openai.resources.completions ^
    --hidden-import openai.resources.embeddings ^
    --hidden-import openai.types ^
    --hidden-import openai.types.chat ^
    --hidden-import openai.types.chat.chat_completion ^
    --hidden-import openai.types.chat.chat_completion_chunk ^
    --hidden-import openai.types.audio ^
    --hidden-import openai.types.audio.transcription ^
    --hidden-import azure.cognitiveservices.speech ^
    --hidden-import azure.cognitiveservices.speech.audio ^
    --hidden-import azure.cognitiveservices.speech.speech ^
    --hidden-import azure.cognitiveservices.speech.translation ^
    --hidden-import azure.cognitiveservices.speech.transcription ^
    --hidden-import azure.cognitiveservices.speech.enums ^
    --hidden-import azure.cognitiveservices.speech.properties ^
    --hidden-import azure.cognitiveservices.speech.interop ^
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
    --hidden-import httpcore ^
    --hidden-import httpcore._sync ^
    --hidden-import httpcore._async ^
    --hidden-import httpcore._sync.http_proxy ^
    --hidden-import httpcore._sync.socks_proxy ^
    --hidden-import httpcore._async.http_proxy ^
    --hidden-import httpcore._async.socks_proxy ^
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