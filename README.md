# 🎓 LecTrans - Real-time Korean → Chinese Lecture Translator

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![MiMo](https://img.shields.io/badge/MiMo-v2.5-orange.svg)

[English](#-english) · [简体中文](#-简体中文)

</div>

---

## 🇬🇧 English

### Overview

LecTrans is a desktop translation tool built for Chinese students studying in South Korea.
It captures lecture audio in real time, transcribes Korean speech, translates it into Chinese
with Xiaomi **MiMo**, and shows both languages side by side. After class it generates structured
notes, saves recordings, and exports Markdown.

Developed with the help of [MiMo Code](https://mimo.xiaomi.com), it targets four pain points:

- 🎧 **Language barrier**: Korean lectures are hard to follow in real time
- 📝 **Note-taking**: manual translation cannot keep up with the lecture
- 🔇 **Classroom etiquette**: fully silent, dark UI, no disturbance
- 📚 **Review**: bilingual records and structured summaries are saved automatically

### Features

| Feature | Description |
|---------|-------------|
| Dual ASR engines | Local faster-whisper (offline, adaptive energy VAD) or Azure Speech (cloud) |
| Context-aware translation | Recent N bilingual pairs are sent as context for term/pronoun consistency |
| Term glossary | Built-in Korean–Chinese CS glossary injected into the prompt |
| Single audio pipeline | One microphone stream feeds both ASR and recording (no device contention) |
| Recording archive | Streams WAV to disk while recording; converts to MP3 on stop (falls back to WAV) |
| One-click summary | Structured notes: key concepts / knowledge points / assignments / open questions |
| History manager | Session list, bilingual review, playback, reveal in folder, delete, Markdown export |
| Silent mode | Apple-inspired dark UI, no audio output |

### Roadmap

- [ ] **MiMo TTS speech playback**: synthesize translations to speech and play quietly through earphones
- [ ] Streaming translation output (currently sentence-based)
- [ ] PDF / Word export
- [ ] More language pairs (English, Japanese)

### Architecture

```
┌──────────────┐   ┌────────────────────┐   ┌──────────────┐   ┌────────────┐
│ AudioRecorder│──▶│ ASR                │──▶│ Translation  │──▶│ UI (2 cols)│
│ single stream│   │ faster-whisper/Azure│  │ MiMo+context │   │ tkinter    │
└──────┬───────┘   └────────────────────┘   └──────────────┘   └─────┬──────┘
       │ streams WAV to disk                                          │
       ▼                                                             ▼
   MP3 archive ◀──────────────────────────────────────────  SessionManager
                                                             (JSON + Markdown)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

### Quick Start

Requirements: Python 3.11+, microphone access, a MiMo API key (Azure key only for the Azure engine).

```bash
pip install -r requirements.txt
python main.py
```

On first launch the settings dialog opens automatically: enter your MiMo API key and choose
**local** (faster-whisper, downloads the model on first run) or **azure** (Azure Speech key required).

Configuration options:

1. **In-app settings** (recommended) — keys are stored in the system keyring when available
2. **Environment variables** — see [.env.example](.env.example) (`LECTRANS_*` overrides)
3. **Config file** — `~/.lectrans/config.json` (only used when keyring is unavailable)

### Build Windows EXE

```bat
build.bat
```

Produces `dist\LecTrans.exe` from a portable [LecTrans.spec](LecTrans.spec) (no hard-coded paths).
Note: the exe bundles the Azure engine only; use the source install for offline faster-whisper.
See [BUILD_GUIDE.md](BUILD_GUIDE.md).

### Testing

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -t . -v   # or pytest
python -m ruff check .
```

CI (GitHub Actions) runs unit tests, compile checks and ruff on Windows.

### Project Layout

```
lectrans/
├── main.py                  # entry point (dotenv → logging → UI)
├── config.py                # JSON + keyring + env overrides
├── core/                    # audio pipeline, recognizers, translator, sessions, logging
├── ui/                      # tkinter UI (design system, main window, dialogs)
├── prompts/templates.py     # translation / summary prompts and glossary
├── tests/                   # unittest suite (optional deps auto-skipped)
├── docs/                    # PRD / architecture / UI spec
└── LecTrans.spec            # portable PyInstaller config
```

### Data Directory

| Path | Content |
|------|---------|
| `~/.lectrans/config.json` | Settings (`LECTRANS_HOME` overrides the root) |
| `~/.lectrans/sessions/` | Session JSON files |
| `~/.lectrans/recordings/` | Lecture recordings (WAV/MP3) |
| `~/.lectrans/lectrans.log` | Rotating log (1MB × 3) |

### License

MIT License, see [LICENSE](LICENSE).

---

## 🇨🇳 简体中文

### 项目简介

LecTrans 是一款专为在韩中国留学生打造的实时课堂翻译桌面工具：课堂上采集教授语音，
识别为韩语文本后调用小米 **MiMo** 大模型翻译成中文，双栏对照展示；课后自动保存录音与
会话，生成结构化笔记并导出 Markdown。

项目在 [MiMo Code](https://mimo.xiaomi.com) 协助下完成开发，主要解决四个痛点：

- 🎧 **语言障碍**：韩语授课实时听不懂
- 📝 **笔记效率**：手动翻译跟不上课堂节奏
- 🔇 **课堂礼仪**：全程静音、暗色界面，不打扰他人
- 📚 **课后复习**：自动保存双语记录与课堂总结

### 功能特性

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

### 路线图

- [ ] **MiMo TTS 语音播报**：将译文实时合成为语音，通过耳机低音量播放，进一步跨越语言障碍
- [ ] 翻译流式输出（当前为整句返回）
- [ ] 导出 PDF / Word
- [ ] 多语言对扩展（英语、日语）

### 架构

```
┌──────────────┐   ┌────────────────────┐   ┌──────────────┐   ┌────────────┐
│ AudioRecorder│──▶│ ASR                │──▶│ 翻译 Worker   │──▶│ UI 双栏展示 │
│ 单路采集      │   │ faster-whisper/Azure│  │ MiMo + 上下文 │   │ tkinter    │
└──────┬───────┘   └────────────────────┘   └──────────────┘   └─────┬──────┘
       │ 边录边写 WAV                                                │
       ▼                                                             ▼
   MP3 存档 ◀──────────────────────────────────────────────  SessionManager
                                                              (JSON + Markdown)
```

详细设计见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

### 快速开始

环境要求：Python 3.11+、麦克风权限、MiMo API Key（仅 Azure 引擎需要 Azure Key）。

```bash
pip install -r requirements.txt
python main.py
```

首次启动会自动弹出设置窗口：填入 MiMo API Key，并选择 **local**（本地 faster-whisper，
首次运行自动下载模型）或 **azure**（需要 Azure Speech Key）。

配置方式：

1. **应用内设置**（推荐）：密钥优先写入系统钥匙串
2. **环境变量覆盖**：见 [.env.example](.env.example)，支持 `LECTRANS_*` 变量
3. **配置文件**：`~/.lectrans/config.json`（keyring 不可用时密钥才落盘）

### 打包 Windows EXE

```bat
build.bat
```

产物为 `dist\LecTrans.exe`（基于可移植的 [LecTrans.spec](LecTrans.spec)，无硬编码路径）。
注：exe 内置 Azure 引擎；需要本地 faster-whisper 离线识别时请用源码运行。
详见 [BUILD_GUIDE.md](BUILD_GUIDE.md)。

### 测试

```bash
pip install -r requirements-dev.txt
python -m unittest discover -s tests -t . -v   # 或 pytest
python -m ruff check .
```

CI（GitHub Actions）在 Windows 上运行单元测试、编译检查与 ruff 检查。

### 目录结构

```
lectrans/
├── main.py                  # 入口（加载 .env、初始化日志、启动 UI）
├── config.py                # 配置：JSON + keyring + 环境变量覆盖
├── core/                    # 音频管线、识别器、翻译、会话、日志
├── ui/                      # tkinter 界面（设计系统、主窗、对话框）
├── prompts/templates.py     # 翻译/总结 Prompt 与术语表
├── tests/                   # unittest 测试（可选依赖自动跳过）
├── docs/                    # PRD / 架构 / UI 规范
└── LecTrans.spec            # 可移植 PyInstaller 配置
```

### 数据目录

| 路径 | 内容 |
|------|------|
| `~/.lectrans/config.json` | 配置（可用 `LECTRANS_HOME` 覆盖根目录） |
| `~/.lectrans/sessions/` | 会话 JSON |
| `~/.lectrans/recordings/` | 课堂录音（WAV/MP3） |
| `~/.lectrans/lectrans.log` | 运行日志（滚动 1MB × 3） |

### License

MIT License，详见 [LICENSE](LICENSE)。

---

<div align="center">

**Made with ❤️ for international students in South Korea · Built with MiMo Code**

</div>
