# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('prompts', 'prompts'),
        ('core', 'core'),
    ],
    hiddenimports=[
        'openai',
        'groq',
        'httpx',
        'pydantic',
        'pydantic_core',
        'anyio',
        'sniffio',
        'distro',
        'jiter',
        'h11',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest',
        'pytest',
        'numpy',
        'pandas',
        'matplotlib',
        'PIL',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='LecTrans',
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
    icon=None,
)
