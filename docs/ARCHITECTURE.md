# LecTrans - 技术架构设计

> 本文档描述 v0.2 重构后的实际架构（单路音频管线 + 异步翻译 + 惰性导入）。

## 1. 系统架构图

```
┌───────────────────────────────────────────────────────────────────────┐
│                           LecTrans 进程                                │
│                                                                       │
│  ┌────────────────┐        ┌───────────────────────────────┐          │
│  │ AudioRecorder  │        │  识别线程（local 或 azure）    │          │
│  │ 采集线程        │ 队列   │  - 自适应能量 VAD（local）     │          │
│  │ - 单路 PyAudio │───────▶│  - Azure 连续识别事件          │          │
│  │ - 边录边写 WAV │        └───────────────┬───────────────┘          │
│  │ - 订阅分发     │                        │ on_recognized(韩语)       │
│  └───────┬────────┘                        ▼                          │
│          │                      ┌───────────────────────┐             │
│          │                      │ 翻译队列 (maxsize=64)  │             │
│          │                      └───────────┬───────────┘             │
│          │                                  ▼                         │
│          │                      ┌───────────────────────┐             │
│          │                      │ 翻译 Worker 线程       │             │
│          │                      │ MiMo + 最近 N 条上下文 │             │
│          │                      └───────────┬───────────┘             │
│          │                                  │ msg_queue             │
│          │                                  ▼                       │
│          │                      ┌───────────────────────┐             │
│          │                      │ 主线程 (tkinter)       │             │
│          │                      │ after(100ms) 消费队列  │             │
│          │                      │ 双栏渲染 / 状态更新    │             │
│          │                      └───────────┬───────────┘             │
│          │                                  │                         │
│          ▼                                  ▼                         │
│   stop() 后 MP3 转换 ──────────▶ SessionManager 自动保存（JSON + 录音）│
└───────────────────────────────────────────────────────────────────────┘
```

## 2. 模块划分

```
lectrans/
├── main.py                    # 入口：dotenv → setup_logging → LecTransApp
├── config.py                  # AppConfig：JSON + keyring + 环境变量覆盖
├── core/
│   ├── audio_recorder.py      # AudioRecorder / AudioManager
│   ├── local_recognizer.py    # LocalWhisperRecognizer（消费共享队列）
│   ├── azure_recognizer.py    # AzureSpeechRecognizer（PushAudioInputStream）
│   ├── translator.py          # MiMoClient（翻译/总结，重试 + 上下文）
│   ├── session_manager.py     # SessionManager / TranscriptEntry
│   ├── platform_utils.py      # open_path / reveal_in_folder
│   ├── logger.py              # setup_logging / get_logger
│   └── types.py               # TranscriptionResult
├── prompts/templates.py       # 翻译/总结 Prompt + CS 术语表
├── ui/
│   ├── app.py                 # 主窗口与线程接线
│   ├── design.py              # DesignSystem：颜色/字体/控件工厂
│   ├── settings_dialog.py     # 设置对话框
│   └── history_dialog.py      # 历史记录对话框
└── tests/                     # unittest 测试套件
```

## 3. 核心设计决策

### 3.1 单路音频管线（解决设备争抢）

旧版由识别器和录音器各自 `pyaudio.open()`，双流并发存在争抢、失败与采样不同步风险。
重构后仅 `AudioRecorder` 持有麦克风：

- 采集线程按 `chunk_size=1024`（16kHz 下 64ms）读取 PCM
- 录声音轨直接 `wave.writeframes()` 落盘，长课堂不再把整段 PCM 留在内存
- 通过 `subscribe()` 向消费者分发，队列满时**丢弃最旧块**，保证实时性
- Azure 模式使用 `PushAudioInputStream` 推送同一数据流，设备选择与录音完全一致

### 3.2 识别与翻译解耦（解决阻塞）

旧版在识别回调中同步调用翻译 API，会阻塞识别循环/事件线程。
现在识别回调只做 `translation_queue.put()`（超时 5s，满则丢弃并告警），
翻译 Worker 串行处理并在 HTTP 层重试，UI 始终不阻塞。

### 3.3 翻译上下文与术语增强

`MiMoClient.translate()` 支持传入最近 N 条（配置 `translation_context_size`，默认 5）双语对照，
与系统 Prompt 中的 CS 术语表一起注入，改善指代和术语一致性。

### 3.4 会话收尾异步化

停止录音后由 finalizer 线程等待翻译队列排空（最多 60s），
再通过 `msg_queue` 通知主线程保存会话，避免 UI 卡顿且不丢最后一两句翻译。
`session_token` 机制确保已过期会话的迟到结果不会写入新会话。

### 3.5 惰性导入（PEP 562）

`core/__init__.py` 使用模块级 `__getattr__` 按需加载子模块：
只装本地依赖的用户不再因为缺少 Azure SDK 而无法 `import core`。

## 4. 数据流

### 4.1 实时翻译

```
点击开始 → AudioRecorder.start()（采集+落盘线程）
        → recognizer.start_continuous_recognition(queue)
        → 识别结果 → 翻译队列 → 翻译 Worker → msg_queue → 主线程渲染
```

### 4.2 停止与存档

```
点击停止 → recognizer.stop() → AudioRecorder.stop()（返回 WAV 路径）
        → 翻译队列置入哨兵 → finalizer 等待 Worker 结束
        → 主线程：WAV → MP3（失败则保留 WAV，记录真实路径）
        → SessionManager.save_session(JSON)
```

## 5. 本地 VAD 设计

- **能量门限**：`threshold = max(energy_threshold, noise_floor × 3.0)`
- **底噪估计**：非语音段对 RMS 做 EMA（0.95/0.05），自动适应环境噪声
- **断句**：连续静音 ≥ `silence_duration`（默认 0.8s）
- **最长句**：累计语音 ≥ `max_utterance_seconds`（默认 20s）强制切分，防止延迟膨胀
- **过滤**：短于 `min_speech_duration`（0.5s）的片段丢弃
- 推理侧再启用 faster-whisper 的 `vad_filter=True` 二次过滤

## 6. 错误处理与可观测性

| 机制 | 说明 |
|------|------|
| 日志 | `core/logger.py`，滚动文件 `~/.lectrans/lectrans.log` + 控制台 |
| API 重试 | 翻译/总结失败重试 2 次（1s/2s 退避），仍失败返回占位文本 |
| 识别错误 | 通过 `on_error` 回调 → 消息队列 → 主线程弹窗 |
| 损坏数据 | 会话 JSON 解析失败跳过并告警，不影响列表 |
| 录音回退 | pydub/ffmpeg 缺失时自动保留 WAV，会话记录真实路径 |

## 7. 配置与安全

- 配置优先级：**环境变量 > keyring > config.json > 默认值**
- API Key 优先写入系统钥匙串；不可用时才写入 JSON（POSIX 下限制为 600）
- 配置文件原子写入（临时文件 + `os.replace`）
- 本地引擎音频不出本机；云端引擎音频发送至 Azure Speech

## 8. 打包

- `LecTrans.spec` 通过 `collect_all("azure.cognitiveservices.speech")` 自动收集 SDK 原生 DLL，
  `collect_submodules` 收集 openai/keyring，**不含任何本机绝对路径**
- exe 面向 Azure 引擎；`numpy`/`faster_whisper` 等本地引擎依赖被排除以控制体积
- CI 在 `workflow_dispatch` 时于 Windows 上构建并上传产物

## 9. 已知限制

- 翻译为整句返回，尚未流式输出
- 本地引擎首次运行需下载 Whisper 模型，且未打包进 exe
- 仅支持韩→中（语言对在设置中预留）
- MiMo TTS 语音播报为路线图功能，尚未实现
