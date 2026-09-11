# -*- mode: python ; coding: utf-8 -*-
"""
LecTrans PyInstaller 打包配置（可移植版）

- 通过 collect_all 自动收集 Azure Speech SDK 的 DLL 与子模块，不再硬编码本机路径
- 自动收集 openai / keyring 子模块，避免 hidden-import 漏项
- exe 为 Azure 引擎版本：本地 faster-whisper 依赖体积过大且需下载模型，
  如需本地引擎请使用 Python 源码运行（详见 BUILD_GUIDE.md）
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = []

# Azure Speech SDK（含跨平台原生 DLL）
az_datas, az_binaries, az_hidden = collect_all("azure.cognitiveservices.speech")
datas += az_datas
binaries += az_binaries
hiddenimports += az_hidden

# 其余动态导入
hiddenimports += collect_submodules("openai")
hiddenimports += collect_submodules("keyring.backends")
hiddenimports += ["pyaudio", "pydub", "dotenv", "tkinter", "tkinter.ttk"]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "numpy",
        "faster_whisper",
        "ctranslate2",
        "tokenizers",
        "onnxruntime",
        "av",
        "pandas",
        "matplotlib",
        "PIL",
        "groq",
        "pytest",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="LecTrans",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
