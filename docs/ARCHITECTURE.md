# LecTrans - 技术架构设计

## 1. 系统架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      LecTrans 系统架构                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   音频采集    │───▶│   语音识别    │───▶│   翻译引擎    │  │
│  │  PyAudio     │    │  Groq Whisper │    │  DeepSeek    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                    状态管理器                         │  │
│  │              (Session State Manager)                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│                            ▼                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   UI 展示     │◀──│   总结引擎    │◀──│   存档管理    │  │
│  │  Streamlit   │    │  LLM Summary │    │  Markdown    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 2. 模块设计

### 2.1 模块划分

```
lectrans/
├── main.py                 # 主入口
├── config.py               # 配置管理
├── core/
│   ├── audio_capture.py    # 音频采集模块
│   ├── speech_recognizer.py # 语音识别模块
│   ├── translator.py       # 翻译模块
│   ├── summarizer.py       # 总结模块
│   └── session_manager.py  # 会话管理
├── services/
│   ├── groq_service.py     # Groq API 封装
│   ├── deepseek_service.py # DeepSeek API 封装
│   └── openai_service.py   # OpenAI 兼容 API 封装
├── ui/
│   ├── app.py              # Streamlit 主界面
│   ├── components.py       # UI 组件
│   └── styles.css          # 样式文件
├── utils/
│   ├── audio_utils.py      # 音频工具函数
│   ├── text_utils.py       # 文本工具函数
│   └── file_utils.py       # 文件工具函数
├── prompts/
│   ├── translation.py      # 翻译 Prompt
│   └── summary.py          # 总结 Prompt
├── requirements.txt        # 依赖列表
└── README.md               # 说明文档
```

### 2.2 核心模块设计

#### 2.2.1 音频采集模块 (audio_capture.py)

```python
class AudioCapture:
    """音频采集器，负责从麦克风捕获音频流"""
    
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
    
    def start(self):
        """开始录音"""
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        self.is_recording = True
    
    def stop(self):
        """停止录音"""
        self.is_recording = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
    
    def read_chunk(self) -> bytes:
        """读取一个音频块"""
        if self.is_recording and self.stream:
            return self.stream.read(self.chunk_size)
        return b""
```

#### 2.2.2 语音识别模块 (speech_recognizer.py)

```python
class SpeechRecognizer:
    """语音识别器，使用 Groq Whisper API"""
    
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.buffer = []
        self.buffer_duration = 3  # 3 秒缓冲
    
    async def transcribe(self, audio_chunk: bytes) -> Optional[str]:
        """转录音频块"""
        self.buffer.append(audio_chunk)
        
        # 检查缓冲区是否达到阈值
        if self._buffer_duration() >= self.buffer_duration:
            audio_data = self._merge_buffer()
            return await self._call_api(audio_data)
        
        return None
    
    async def _call_api(self, audio_data: bytes) -> str:
        """调用 Groq Whisper API"""
        response = await self.client.audio.transcriptions.create(
            file=("audio.wav", audio_data),
            model="whisper-large-v3-turbo",
            language="ko"
        )
        return response.text
```

#### 2.2.3 翻译模块 (translator.py)

```python
class Translator:
    """翻译器，使用 OpenAI 兼容 API"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.history = []
    
    async def translate(self, korean_text: str) -> str:
        """翻译韩语为中文"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": TRANSLATION_PROMPT},
                {"role": "user", "content": korean_text}
            ],
            stream=True
        )
        
        # 流式返回翻译结果
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
```

#### 2.2.4 总结模块 (summarizer.py)

```python
class Summarizer:
    """总结生成器"""
    
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    
    async def summarize(self, transcript: str) -> str:
        """生成课堂总结"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": transcript}
            ]
        )
        return response.choices[0].message.content
```

---

## 3. 数据流设计

### 3.1 实时翻译流程

```
用户点击 Start
      │
      ▼
┌─────────────────┐
│  开始音频采集    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  读取音频块     │────▶│  缓冲区累积     │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  检测静音断句    │
                        │  (WebRTC VAD)   │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  发送到 Whisper  │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  获取韩语文本    │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  发送到翻译 API  │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  流式返回中文    │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  更新 UI 显示    │
                        └─────────────────┘
```

### 3.2 总结生成流程

```
用户点击 Summary
      │
      ▼
┌─────────────────┐
│  收集历史记录    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  构建 Prompt    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  调用 LLM API   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  解析返回结果    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  显示总结面板    │
└─────────────────┘
```

---

## 4. API 设计

### 4.1 内部接口

```python
# 音频采集接口
class IAudioCapture(Protocol):
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def read_chunk(self) -> bytes: ...

# 语音识别接口
class ISpeechRecognizer(Protocol):
    async def transcribe(self, audio: bytes) -> Optional[str]: ...

# 翻译接口
class ITranslator(Protocol):
    async def translate(self, text: str) -> AsyncGenerator[str, None]: ...

# 总结接口
class ISummarizer(Protocol):
    async def summarize(self, transcript: str) -> str: ...
```

### 4.2 外部 API 调用

#### Groq Whisper API
```python
# 请求
POST https://api.groq.com/openai/v1/audio/transcriptions
Content-Type: multipart/form-data

file: audio.wav
model: whisper-large-v3-turbo
language: ko

# 响应
{
    "text": "안녕하세요, 오늘 컴퓨터 과학 수업을 시작하겠습니다."
}
```

#### DeepSeek Chat API
```python
# 请求
POST https://api.deepseek.com/v1/chat/completions
Content-Type: application/json

{
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "你是韩中翻译官..."},
        {"role": "user", "content": "안녕하세요..."}
    ],
    "stream": true
}

# 响应 (SSE)
data: {"choices":[{"delta":{"content":"你好"}}]}
data: {"choices":[{"delta":{"content":"，今天"}}]}
...
```

---

## 5. 状态管理

### 5.1 会话状态

```python
@dataclass
class SessionState:
    """会话状态"""
    is_recording: bool = False
    is_connected: bool = False
    
    # 转录记录
    transcripts: List[TranscriptEntry] = field(default_factory=list)
    
    # 翻译记录
    translations: List[TranslationEntry] = field(default_factory=list)
    
    # 总结
    summary: Optional[str] = None
    
    # 配置
    config: AppConfig = field(default_factory=AppConfig)

@dataclass
class TranscriptEntry:
    """转录条目"""
    timestamp: datetime
    korean_text: str
    chinese_text: str
```

### 5.2 状态持久化

```python
class SessionPersistence:
    """会话持久化"""
    
    def save(self, state: SessionState, filepath: str):
        """保存会话到文件"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "transcripts": [
                {
                    "time": t.timestamp.isoformat(),
                    "ko": t.korean_text,
                    "zh": t.chinese_text
                }
                for t in state.transcripts
            ],
            "summary": state.summary
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True)
    
    def load(self, filepath: str) -> SessionState:
        """从文件加载会话"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 转换为 SessionState
        ...
```

---

## 6. 错误处理

### 6.1 错误类型

```python
class LecTransError(Exception):
    """基础异常"""
    pass

class AudioCaptureError(LecTransError):
    """音频采集错误"""
    pass

class APIConnectionError(LecTransError):
    """API 连接错误"""
    pass

class TranscriptionError(LecTransError):
    """转录错误"""
    pass

class TranslationError(LecTransError):
    """翻译错误"""
    pass
```

### 6.2 重试机制

```python
class RetryHandler:
    """重试处理器"""
    
    def __init__(self, max_retries=3, delay=1):
        self.max_retries = max_retries
        self.delay = delay
    
    async def execute(self, func, *args, **kwargs):
        """执行函数，失败时重试"""
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.delay * (attempt + 1))
        
        raise last_error
```

---

## 7. 性能优化

### 7.1 音频缓冲优化
- 使用环形缓冲区，避免内存增长
- 异步读取，不阻塞主线程

### 7.2 API 调用优化
- 流式处理，减少等待时间
- 连接池复用，减少连接开销
- 请求合并，减少 API 调用次数

### 7.3 UI 更新优化
- 虚拟滚动，只渲染可见区域
- 防抖更新，避免频繁刷新

---

## 8. 安全考虑

### 8.1 API Key 保护
- 配置文件加密存储
- 环境变量优先读取
- 不在日志中输出

### 8.2 数据隐私
- 音频数据本地处理，不上传
- 转录记录本地存储
- 支持手动清除记录

---

## 9. 依赖列表

```txt
# requirements.txt

# 音频处理
pyaudio==0.2.14
webrtcvad==2.0.10
numpy==1.26.4

# API 客户端
openai==1.50.0
groq==0.11.0
httpx==0.27.0

# 前端
streamlit==1.39.0

# 工具
pyyaml==6.0.2
python-dotenv==1.0.1
rich==13.9.0

# 可选：PDF 生成
reportlab==4.2.3
```

---

## 10. 开发环境

### 10.1 环境要求
- Python 3.9+
- 系统麦克风权限
- 网络连接（API 调用）

### 10.2 开发工具
- IDE: VS Code / PyCharm
- 包管理: pip / poetry
- 版本控制: Git
