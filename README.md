# 🎓 LecTrans - Real-time Lecture Translation Tool

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)
![MiMo](https://img.shields.io/badge/MiMo-2.5-orange.svg)

**Real-time Korean-to-Chinese lecture translation tool for international students**

[Features](#features) • [Quick Start](#quick-start) • [Architecture](#architecture) • [Documentation](#documentation)

</div>

---

## 🎯 Overview

LecTrans is designed specifically for Chinese students studying in South Korea. It provides **real-time speech recognition** and **translation** during lectures, helping students overcome language barriers and improve learning efficiency.

### Core Pain Points Solved

- 🎧 **Language Barrier**: Korean lectures are difficult to understand in real-time
- 📝 **Note-taking Efficiency**: Manual translation slows down note-taking
- 🔇 **Classroom Etiquette**: Existing tools require audio output, disturbing classmates
- 📚 **Post-class Review**: No organized bilingual notes for review

## ✨ Features

- **Real-time ASR**: MiMo-V2.5-ASR for Korean speech recognition
- **Accurate Translation**: MiMo-2.5-Pro for context-aware translation
- **Silent Mode**: Dark theme UI, no audio output
- **Session Management**: Save and review lecture history
- **Windows EXE**: One-click packaging for easy distribution
- **Multi-Agent Architecture**: Parallel processing for low latency

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MiMo API Key ([Get one here](https://mimo.xiaomi.com))

### Installation

```bash
# Clone the repository
git clone https://github.com/forhetale/lectrans.git
cd lectrans

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env and add your MIMO_API_KEY

# Run the application
python lectrans_gui_v4.py
```

### Build Windows EXE

```bash
# Run the build script
build_mimo.bat
```

The executable will be created in the `dist/` directory.

## 🏗️ Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Audio      │ →  │  ASR        │ →  │  Text       │ →  │  Translation│
│  Capture    │    │  (MiMo)     │    │  Processing │    │  (MiMo)     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       ↓                  ↓                  ↓                  ↓
   Device Select    Korean Recognition   Term Matching    Chinese Translation
   3s Buffer        Confidence Filter    Context Memory   Quality Assessment
```

### Multi-Agent Collaboration

| Agent | Responsibility | Model |
|-------|---------------|-------|
| Audio Agent | Real-time audio capture & buffering | - |
| ASR Agent | Korean speech-to-text | MiMo-V2.5-ASR |
| Text Agent | Cleaning, term matching, context | - |
| Translation Agent | Korean → Chinese translation | MiMo-2.5-Pro |
| Session Agent | History management & export | - |

## 📖 Documentation

- [Product Requirements Document](docs/PRD.md)
- [Architecture Design](docs/ARCHITECTURE.md)
- [UI Design Specification](docs/UI-DESIGN.md)
- [Build Guide](BUILD_GUIDE.md)
- [Windows EXE Guide](EXE_README.md)

## 🔧 Configuration

### Environment Variables

```env
MIMO_API_KEY=your_api_key_here
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL_ASR=mimo-v2.5-asr
MIMO_MODEL_TRANSLATION=mimo-v2.5-pro
```

### Audio Settings

- **Sample Rate**: 16kHz
- **Buffer Size**: 3 seconds
- **Channels**: Mono

## 📊 Performance Metrics

| Metric | Value |
|--------|-------|
| ASR Latency | < 1s |
| Translation Latency | < 2s |
| End-to-End Latency | < 3s |
| ASR Accuracy | > 95% |
| Translation Quality | > 90% |

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **GUI**: tkinter (dark theme)
- **Audio**: PyAudio
- **ASR**: MiMo-V2.5-ASR
- **Translation**: MiMo-2.5-Pro
- **Packaging**: PyInstaller

## 📈 Token Consumption (Daily - 4 hours lecture)

| Component | Tokens/Day |
|-----------|------------|
| ASR | ~1,000,000 |
| Translation | ~500,000 |
| Summary | ~20,000 |
| **Total** | **~1,520,000** |

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [MiMo](https://mimo.xiaomi.com) for providing ASR and translation APIs
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) for audio capture
- [tkinter](https://docs.python.org/3/library/tkinter.html) for GUI framework

---

<div align="center">

**Made with ❤️ for international students in South Korea**

[Report Bug](https://github.com/forhetale/lectrans/issues) • [Request Feature](https://github.com/forhetale/lectrans/issues)

</div>
