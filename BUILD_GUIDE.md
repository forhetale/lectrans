# LecTrans 构建与打包指南

## 方式一：源码运行（推荐，功能完整）

适用于开发与需要**本地 faster-whisper 离线识别**的场景。

```bash
# 1. 创建虚拟环境（Python 3.11+）
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python main.py
```

首次使用本地引擎时会自动下载 Whisper 模型（`tiny`/`base`/`small`…，越大越准也越慢）。

## 方式二：打包 Windows EXE

```bat
build.bat
```

脚本会安装依赖并调用 [LecTrans.spec](LecTrans.spec) 生成 **`dist\LecTrans.exe`**（约 90-120MB）。

> ⚠️ exe 内置 **Azure Speech** 引擎。
> 本地 faster-whisper 因依赖体积过大（ctranslate2 / tokenizers / onnxruntime 等）未打包，
> 如需离线识别请使用方式一源码运行。

## 方式三：GitHub Actions 云端构建

仓库内置 `.github/workflows/ci.yml`：

- `push / PR`：在 Windows 上运行单元测试、编译检查与 ruff
- `workflow_dispatch`（手动触发）：执行 PyInstaller 构建并上传 `LecTrans-windows` 产物

## spec 说明（可移植）

`LecTrans.spec` 已移除旧版的硬编码绝对路径：

- `collect_all("azure.cognitiveservices.speech")` 自动收集 SDK 原生 DLL
- `collect_submodules("openai")` / `collect_submodules("keyring.backends")` 自动收集隐藏导入
- `excludes` 排除 numpy / faster_whisper 等本地引擎依赖以控制体积

## 常见问题

**Q: 打包后 exe 很大？**
A: 正常。Python 运行时 + Azure SDK + OpenAI SDK 都在其中。

**Q: 杀毒软件报警？**
A: PyInstaller onefile 常见误报，添加白名单即可。

**Q: exe 启动后提示无法使用本地识别？**
A: 在「设置」中把引擎切换为 **azure**，或改用源码方式运行。

**Q: 打包失败提示找不到 Azure DLL？**
A: 确认已安装 `azure-cognitiveservices-speech`，spec 会自动定位；无需手动配置路径。

**Q: 如何减小体积？**
A: 保持 spec 中的 `excludes`；如需 UPX 压缩请自行安装并确认不再使用 `upx=True` 的兼容性问题。
