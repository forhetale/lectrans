# 🎓 LecTrans - 实时课堂翻译工具

> "无感、精准、实时的学术助听器" —— 专为在韩国留学的中国学生设计

## ✨ 功能特点

- **实时双语流**：韩语原文 + 中文翻译并排显示
- **一键智能总结**：自动生成结构化课堂笔记
- **静音模式**：暗黑界面，不打扰他人
- **多 API 支持**：小米 MiMo、DeepSeek、OpenAI 等
- **笔记存档**：导出 Markdown 格式笔记

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置 API

创建 `.env` 文件：

```env
# 语音识别 (Groq - 免费)
GROQ_API_KEY=your_groq_api_key

# 翻译/总结 (小米 MiMo)
XIAOMI_API_KEY=your_xiaomi_api_key
XIAOMI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
XIAOMI_MODEL=mimo-v2.5-pro
```

### 3. 启动应用

```bash
python run.py
```

访问 http://localhost:8501

## 📖 使用说明

### 基本流程

1. **配置 API**：首次使用需配置 ASR 和 LLM API Key
2. **开始录音**：点击 "▶️ Start" 按钮
3. **实时翻译**：韩语原文和中文翻译并排显示
4. **生成总结**：点击 "📝 Summary" 生成课堂笔记
5. **导出笔记**：点击 "📥 Export" 导出 Markdown

## 🛠️ 技术架构

```
音频采集 (PyAudio)
      ↓
语音识别 (Groq Whisper)
      ↓
实时翻译 (MiMo 2.5 Pro)
      ↓
界面展示 (Streamlit)
```

## 🔑 API 配置说明

### Groq Whisper (语音识别)

| 项目 | 说明 |
|------|------|
| 用途 | 韩语语音转文字 |
| 获取地址 | https://console.groq.com |
| 免费额度 | 每分钟 800+ 次请求 |
| 推荐模型 | whisper-large-v3-turbo |

### 小米 MiMo (翻译/总结)

| 项目 | 说明 |
|------|------|
| 用途 | 韩中翻译 + 课堂总结 |
| 获取地址 | https://mimo.xiaomi.com |
| Base URL | https://token-plan-cn.xiaomimimo.com/v1 |
| 推荐模型 | mimo-v2.5-pro |

### 其他支持的 API

| 提供商 | Base URL | 模型 |
|--------|----------|------|
| DeepSeek | https://api.deepseek.com/v1 | deepseek-chat |
| OpenAI | https://api.openai.com/v1 | gpt-4o |
| Groq | https://api.groq.com/openai/v1 | llama-3.3-70b-versatile |
| LM Studio | http://localhost:1234/v1 | 自定义 |

## 📁 项目结构

```
lectrans/
├── run.py              # 启动脚本
├── config.py           # 配置管理
├── requirements.txt    # 依赖列表
├── .env.example        # 环境变量模板
├── core/               # 核心模块
│   ├── audio_capture.py
│   ├── speech_recognizer.py
│   ├── translator.py
│   └── session_manager.py
├── prompts/            # Prompt 模板
├── ui/                 # 界面
│   └── app.py
└── docs/               # 文档
```

## 💡 使用技巧

1. **降低延迟**：使用 Groq Whisper API，延迟可低至 1 秒
2. **提高准确率**：MiMo 对中文优化更好，翻译质量高
3. **课堂使用**：使用暗黑模式，降低屏幕亮度
4. **网络不稳定**：支持断网缓存，网络恢复后补翻

## 🐛 常见问题

### Q: MiMo API 如何获取？
A: 访问 https://mimo.xiaomi.com 注册并获取 API Key

### Q: 翻译延迟太高？
A: MiMo 服务器在国内，延迟通常较低。如仍有问题，可尝试 DeepSeek。

### Q: 专业术语不准？
A: Prompt 中已内置计算机专业术语词典，会自动优化翻译。

## 📄 许可证

MIT License
