# LecTrans Windows 打包指南

## 方法一：在 Windows 上本地打包（推荐）

### 前提条件
- Windows 10/11
- Python 3.9+ 已安装
- 网络连接

### 步骤

#### 1. 下载项目
将整个 `lectrans` 文件夹复制到 Windows 电脑

#### 2. 运行打包脚本
双击 `build_windows.bat`，等待完成

#### 3. 获取 exe
打包完成后，`dist\LecTrans.exe` 就是可执行文件

---

## 方法二：使用 GitHub Actions 自动打包

如果有 GitHub 账号，可以使用以下工作流自动打包：

### 1. 创建 GitHub 仓库
上传项目到 GitHub

### 2. 添加工作流
创建 `.github/workflows/build.yml`：

```yaml
name: Build LecTrans

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  build:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build exe
      run: |
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
          gui_app.py
    
    - name: Upload artifact
      uses: actions/upload-artifact@v3
      with:
        name: LecTrans
        path: dist/LecTrans.exe
```

### 3. 下载 exe
在 Actions 页面下载打包好的 exe 文件

---

## 方法三：使用在线打包服务

### PyInstaller Online
https://www.pyinstaller.org/

### Nuitka
https://nuitka.net/

---

## 常见问题

### Q: 打包后 exe 很大？
A: 正常，Python 运行时和依赖都会打包进去，通常 30-50MB

### Q: 杀毒软件报警？
A: PyInstaller 打包的程序可能被误报，添加白名单即可

### Q: 运行时缺少 DLL？
A: 确保在 Windows 上打包，不要跨平台打包

### Q: 如何减小体积？
A: 使用 UPX 压缩：https://upx.github.io/

---

## 快速打包命令（Windows CMD）

```cmd
cd lectrans
pip install -r requirements.txt pyinstaller
pyinstaller --onefile --windowed --name LecTrans gui_app.py
```

打包完成后，`dist\LecTrans.exe` 就是可执行文件
