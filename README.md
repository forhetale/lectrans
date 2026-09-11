# 🎓 LecTrans - 实时韩中课堂翻译工具

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![MiMo](https://img.shields.io/badge/MiMo-v2.5-orange.svg)

**面向在韩中国留学生的实时课堂翻译桌面工具**

</div>

---

## 🎯 项目简介

LecTrans 专为在韩国留学的中国学生设计：课堂上实时采集教授语音，识别为韩语文本，
调用小米 MiMo 大模型翻译成中文，双栏对照展示；课后可生成结构化笔记、回看历史、导出 Markdown。

项目在 [MiMo Code](https://mimo.xiaomi.com) 协助下完成开发，主要解决四个痛点：

- 🎧 **语言障碍**：韩语授课实时听不懂
- 📝 **笔记效率**：手动翻译跟不上课堂节奏
- 🔇 **课堂礼仪**：全程静音、暗色界面，不打扰他人
- 📚 **课后复习**：自动保存双语记录与课堂总结

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 双 ASR 引擎 | 本地 faster-whisper（离线、自适应能量 VAD）或 Azure Speech（云端） |
| 上下文翻译 | 翻译时携带最近 N 条双语对照，术语与指代更连贯 |
| 术语增强 | 内置计算机韩中术语表，Prompt 自动注入 |
| 单路音频管线 | 一次采集同时用于识别与录音，避免设备争抢 |
| 录音存档 | 边录边写 WAV，停止后转 MP3（缺 ffmpeg 自动回退 WAV） |
| 一键总结 | 生成「核心概念 / 重要知识点 / 作业考试 / 待确认问题」结构化笔记 |
| 历史管理 | 会话列表、双语回看、录音播放、定位文件、删除、导出 Markdown |
| 安静模式 | Apple 风格深色 UI，无任何声音输出 |

### 🗺️ 路线图

- [ ] **MiMo TTS 语音播报**：将译文实时合成为语音，通过耳机低音量播放，进一步跨越语言障碍
- [ ] 翻译流式输出（当前为整句返回）
- [ ] 导出 PDF / Word
- [ ] 多语言对扩展（英语、日语）

## 🏗️ 架构

```
┌──────────────┐   ┌────────────────────┐   ┌──────────────┐   ┌────────────┐
│ AudioRecorder│──▶│ ASR                 │──▶│ 翻译 Worker   │──▶│ UI 双栏展示 │
│ 单路采集      │   │ faster-whisper/Azure│   │ MiMo + 上下文 │   │ tkinter    │
└──────┬───────┘   └────────────────────┘   └──────────────┘   └─────┬──────┘
       │ 边录边写 WAV                                                 │
       ▼                                                             ▼
   MP3 存档 ◀──────────────────────────────────────────────  SessionManager
                                                              (JSON + Markdown)
```

详细设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

## 🚀 快速开始

### 环境要求

- Python 3.11+
- 麦克风权限
- MiMo API Key（翻译/总结，必填）；本地模式无需 Azure

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动
python main.py

# 3. 首次启动会自动弹出设置：填入 MiMo API Key
#    本地识别：选择 local + 模型规模（首次运行会自动下载模型）
#    云端识别：选择 azure + 填入 Azure Speech Key
```

### 配置方式

1. **应用内设置**（推荐）：`设置 → 保存`，密钥优先写入系统钥匙串（keyring）
2. **环境变量覆盖**：见 [.env.example](.env.example)，支持 `LECTRANS_*` 变量
3. **配置文件**：`~/.lectrans/config.json`（keyring 不可用时密钥才落盘）

## 📦 打包 Windows EXE

```bat
build.bat
```

产物为 `dist\LecTrans.exe`（基于可移植的 [LecTrans.spec](LecTrans.spec)，无硬编码路径）。
注：exe 内置 Azure 引擎；本地 faster-whisper 体积过大未打包，需要本地离线识别时请用源码运行。
详见 [BUILD_GUIDE.md](BUILD_GUIDE.md)。

## 🧪 测试

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -t . -v   # 或 pytest
python -m ruff check .
```

CI（GitHub Actions）在 Windows 上运行单元测试、编译检查与 ruff 检查。

## 📁 目录结构

```
lectrans/
├── main.py                  # 入口（加载 .env、初始化日志、启动 UI）
├── config.py                # 配置：JSON + keyring + 环境变量覆盖
├── core/
│   ├── audio_recorder.py    # 单路采集、录音落盘、订阅分发
│   ├── local_recognizer.py  # faster-whisper + 自适应 VAD
│   ├── azure_recognizer.py  # Azure Speech（支持共享音频队列）
│   ├── translator.py        # MiMo 翻译/总结（上下文 + 重试）
│   ├── session_manager.py   # 会话存档与 Markdown 导出
│   ├── platform_utils.py    # 跨平台打开文件/文件夹
│   ├── logger.py            # 滚动日志
│   └── types.py             # 统一数据类型
├── ui/                      # tkinter 界面（设计系统、主窗、设置、历史）
├── prompts/templates.py     # 翻译/总结 Prompt 与术语表
├── tests/                   # unittest 单元测试（可选依赖自动跳过）
├── docs/                    # PRD / 架构 / UI 规范
└── LecTrans.spec            # 可移植 PyInstaller 配置
```

## 📂 数据目录

| 路径 | 内容 |
|------|------|
| `~/.lectrans/config.json` | 配置（可用 `LECTRANS_HOME` 覆盖根目录） |
| `~/.lectrans/sessions/` | 会话 JSON |
| `~/.lectrans/recordings/` | 课堂录音（WAV/MP3） |
| `~/.lectrans/lectrans.log` | 运行日志（滚动 1MB × 3） |

## 📖 文档

- [产品需求文档](docs/PRD.md)
- [技术架构设计](docs/ARCHITECTURE.md)
- [UI 设计规范](docs/UI-DESIGN.md)
- [打包指南](BUILD_GUIDE.md)

## 📄 License

MIT License，详见 [LICENSE](LICENSE)。

---

<div align="center">

**Made with ❤️ for international students in South Korea · Built with MiMo Code**

</div>
