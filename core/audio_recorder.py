"""
LecTrans 音频录制模块

单路麦克风采集（避免识别器与录音器各自打开设备导致争抢）：
- 后台线程持续读取 PyAudio 数据块
- 边录边写 WAV，长课堂不再把整段 PCM 留在内存
- 通过 subscribe() 向识别器等消费者分发实时音频块，队列满时丢弃最旧数据保证实时性
"""

import queue
import threading
import time
import wave
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import get_logger

logger = get_logger(__name__)


class AudioRecorder:
    """单路音频采集器：录制到磁盘 + 向订阅者分发实时数据块"""

    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        device_index: int = -1,
        output_path: Optional[str] = None,
        consumer_queue_size: int = 512,
    ):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.output_path = Path(output_path) if output_path else None
        self.consumer_queue_size = consumer_queue_size

        self.is_recording = False
        self._audio = None
        self._stream = None
        self._wave = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._consumers: List[queue.Queue] = []
        self._recorded_bytes = 0
        self._start_time: Optional[float] = None

    # ------------------------------------------------------ 生命周期

    def start(self) -> bool:
        """开始采集"""
        if self.is_recording:
            return True
        try:
            import pyaudio
        except ImportError:
            logger.error("PyAudio 未安装，无法采集音频")
            return False

        try:
            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index if self.device_index >= 0 else None,
                frames_per_buffer=self.chunk_size,
            )
        except Exception as e:
            logger.error("打开麦克风失败: %s", e)
            self._close_resources()
            return False

        if self.output_path:
            try:
                self.output_path.parent.mkdir(parents=True, exist_ok=True)
                self._wave = wave.open(str(self.output_path), "wb")
                self._wave.setnchannels(1)
                self._wave.setsampwidth(2)  # 16-bit
                self._wave.setframerate(self.sample_rate)
            except Exception as e:
                logger.error("创建录音文件失败: %s", e)
                self._close_resources()
                return False

        self._recorded_bytes = 0
        self._start_time = time.time()
        self.is_recording = True
        self._thread = threading.Thread(target=self._capture_loop, name="audio-capture", daemon=True)
        self._thread.start()
        logger.info("音频采集已启动 (设备=%s, 输出=%s)", self.device_index, self.output_path)
        return True

    def stop(self) -> Dict:
        """停止采集并返回录音信息"""
        self.is_recording = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

        duration = self.duration()
        self._close_resources()

        info = {
            "path": str(self.output_path) if self.output_path and self._recorded_bytes else "",
            "duration": duration,
            "bytes": self._recorded_bytes,
        }
        logger.info("音频采集已停止 (时长=%.1fs, 大小=%dB)", duration, self._recorded_bytes)
        return info

    def _close_resources(self):
        if self._wave is not None:
            try:
                self._wave.close()
            except Exception:
                pass
            self._wave = None
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._audio is not None:
            try:
                self._audio.terminate()
            except Exception:
                pass
            self._audio = None

    # ------------------------------------------------------ 采集循环

    def _capture_loop(self):
        while self.is_recording and self._stream is not None:
            try:
                chunk = self._stream.read(self.chunk_size, exception_on_overflow=False)
            except Exception as e:
                if self.is_recording:
                    logger.warning("采集异常: %s", e)
                break

            self._recorded_bytes += len(chunk)
            if self._wave is not None:
                try:
                    self._wave.writeframes(chunk)
                except Exception as e:
                    logger.warning("写入录音文件失败: %s", e)
            self._dispatch(chunk)

    def _dispatch(self, chunk: bytes):
        """向所有订阅者分发音频块；队列满时丢弃最旧块"""
        with self._lock:
            consumers = list(self._consumers)

        for q in consumers:
            try:
                q.put_nowait(chunk)
            except queue.Full:
                try:
                    q.get_nowait()
                    q.put_nowait(chunk)
                except (queue.Empty, queue.Full):
                    pass

    # ------------------------------------------------------ 订阅 / 状态

    def subscribe(self, maxsize: Optional[int] = None) -> queue.Queue:
        """订阅实时音频块，返回消费者队列"""
        q: queue.Queue = queue.Queue(maxsize=maxsize or self.consumer_queue_size)
        with self._lock:
            self._consumers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self._consumers:
                self._consumers.remove(q)

    def duration(self) -> float:
        """已录制时长（秒）"""
        if self._recorded_bytes and self.sample_rate:
            return self._recorded_bytes / 2 / self.sample_rate
        if self._start_time is None:
            return 0.0
        return max(0.0, time.time() - self._start_time)

    def recording_size(self) -> int:
        """当前已录制字节数"""
        return self._recorded_bytes

    # ------------------------------------------------------ 文件输出

    @staticmethod
    def save_wav(filepath: str, audio_data: bytes, sample_rate: int = 16000) -> str:
        """将原始 PCM 数据保存为 WAV 文件"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)
        return str(path)

    @staticmethod
    def convert_wav_to_mp3(wav_path: str, mp3_path: str) -> str:
        """WAV 转 MP3；失败时返回 WAV 路径（保证调用方拿到真实存在的文件）"""
        wav = Path(wav_path)
        if not wav.exists():
            return ""

        mp3 = Path(mp3_path)
        mp3.parent.mkdir(parents=True, exist_ok=True)
        try:
            from pydub import AudioSegment

            AudioSegment.from_wav(str(wav)).export(str(mp3), format="mp3")
            if mp3.exists() and mp3.stat().st_size > 0:
                wav.unlink(missing_ok=True)
                return str(mp3)
        except Exception as e:
            logger.warning("MP3 转码失败，保留 WAV: %s", e)

        return str(wav)

    @staticmethod
    def save_mp3(filepath: str, audio_data: bytes, sample_rate: int = 16000) -> str:
        """将原始 PCM 数据保存为 MP3，失败时回退 WAV 并返回真实路径"""
        path = Path(filepath)
        tmp_wav = path.with_suffix(".wav")
        AudioRecorder.save_wav(str(tmp_wav), audio_data, sample_rate)
        final_path = AudioRecorder.convert_wav_to_mp3(str(tmp_wav), str(path))
        if final_path and Path(final_path).suffix.lower() == ".mp3":
            tmp_wav.unlink(missing_ok=True)
        return final_path


class AudioManager:
    """音频设备管理"""

    @staticmethod
    def get_input_devices() -> List[dict]:
        """获取输入设备列表"""
        devices = [{"index": -1, "name": "默认设备"}]
        try:
            import pyaudio

            p = pyaudio.PyAudio()
            try:
                for i in range(p.get_device_count()):
                    try:
                        info = p.get_device_info_by_index(i)
                        if info["maxInputChannels"] <= 0:
                            continue
                        name = info["name"]
                        if isinstance(name, bytes):
                            name = name.decode("utf-8", errors="ignore")
                        name = name.replace("\r", "").replace("\n", " ")
                        devices.append({"index": i, "name": f"{name[:40]} (设备 {i})"})
                    except Exception as e:
                        logger.debug("读取设备 %d 信息失败: %s", i, e)
            finally:
                p.terminate()
        except ImportError:
            logger.warning("PyAudio 未安装，无法枚举音频设备")
        except Exception as e:
            logger.error("枚举音频设备失败: %s", e)
        return devices
