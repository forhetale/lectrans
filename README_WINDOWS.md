# LecTrans - Windows 使用说明

## 直接运行（源码，推荐）

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

首次启动会自动弹出设置窗口，填入 MiMo API Key 即可使用；需要离线识别时在设置中选择 local 引擎。

## 打包 EXE

```cmd
build.bat
```

产物：`dist\LecTrans.exe`（Azure 引擎版）。

## 注意事项

- 需要 Python 3.11+；`pyaudio` 在 Windows 上使用官方 wheel，无需编译
- 本地 Whisper 首次运行会下载模型，建议在网络良好时进行
- 麦克风权限：设置 → 隐私和安全性 → 麦克风 → 允许桌面应用访问
- 完整说明见 [BUILD_GUIDE.md](BUILD_GUIDE.md) 与 [EXE_README.md](EXE_README.md)
