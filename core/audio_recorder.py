"""
LecTrans 音频录制模块
支持实时录制 + 整段保存为 WAV 文件
"""

import io
import wave
import threading
import time
from pathlib import Path


class AudioRecorder:
    """音频录制器，支持实时录制和保存"""

    def __init__(self, sample_rate=16000, chunk_size=1024, device_index=-1):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.is_recording = False
        self._audio = None
        self._stream = None
        self._buffer = []          # 实时识别用（会被取走清空）
        self._full_recording = []  # 完整录音（只增不减）
        self._lock = threading.Lock()

    def start(self) -> bool:
        """开始录音"""
        try:
            import pyaudio
            self._audio = pyaudio.PyAudio()
            self._stream = self._audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index if self.device_index >= 0 else None,
                frames_per_buffer=self.chunk_size,
            )
            self.is_recording = True
            self._buffer = []
            self._full_recording = []
            threading.Thread(target=self._record_loop, daemon=True).start()
            return True
        except ImportError:
            print("PyAudio not installed")
            return False
        except Exception as e:
            print(f"Audio start error: {e}")
            return False

    def stop(self) -> bytes:
        """停止录音并返回完整录音数据"""
        self.is_recording = False
        time.sleep(0.2)

        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass

        if self._audio:
            try:
                self._audio.terminate()
            except Exception:
                pass

        self._stream = None
        self._audio = None

        with self._lock:
            data = b''.join(self._full_recording)
            self._full_recording = []
            self._buffer = []
            return data

    def _record_loop(self):
        """录音循环"""
        while self.is_recording and self._stream:
            try:
                chunk = self._stream.read(self.chunk_size, exception_on_overflow=False)
                with self._lock:
                    self._buffer.append(chunk)
                    self._full_recording.append(chunk)
            except Exception as e:
                if self.is_recording:
                    print(f"Record error: {e}")
                break

    def get_buffer(self) -> bytes:
        """获取并清空识别缓冲区"""
        with self._lock:
            if not self._buffer:
                return b''
            data = b''.join(self._buffer)
            self._buffer = []
            return data

    def buffer_duration(self) -> float:
        """当前缓冲区时长（秒）"""
        with self._lock:
            total_samples = sum(len(c) // 2 for c in self._buffer)
            return total_samples / self.sample_rate

    def recording_size(self) -> int:
        """当前完整录音大小（字节）"""
        with self._lock:
            return sum(len(c) for c in self._full_recording)

    @staticmethod
    def save_wav(filepath: str, audio_data: bytes, sample_rate: int = 16000):
        """将原始 PCM 数据保存为 WAV 文件"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(path), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(audio_data)

    @staticmethod
    def save_mp3(filepath: str, audio_data: bytes, sample_rate: int = 16000):
        """将原始 PCM 数据保存为 MP3 文件"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            from pydub import AudioSegment
            audio = AudioSegment(
                data=audio_data,
                sample_width=2, # 16-bit
                frame_rate=sample_rate,
                channels=1
            )
            audio.export(str(path), format="mp3")
        except Exception as e:
            print(f"Error saving MP3: {e}")
            # Fallback to WAV if MP3 fails
            fallback_path = path.with_suffix('.wav')
            AudioRecorder.save_wav(str(fallback_path), audio_data, sample_rate)


class AudioManager:
    """音频设备管理"""

    @staticmethod
    def get_input_devices():
        """获取输入设备列表"""
        devices = [{'index': -1, 'name': '默认设备'}]
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            for i in range(p.get_device_count()):
                try:
                    info = p.get_device_info_by_index(i)
                    if info['maxInputChannels'] > 0:
                        name = info['name']
                        try:
                            # Try to decode if it's bytes, PyAudio sometimes returns garbled text on Windows
                            if isinstance(name, bytes):
                                name = name.decode('utf-8', errors='ignore')
                        except Exception:
                            pass
                        # Clean up newlines that might break tkinter
                        name = name.replace('\r', '').replace('\n', ' ')
                        devices.append({
                            'index': i,
                            'name': f"{name[:40]} (设备 {i})"
                        })
                except Exception as e:
                    print(f"Error getting info for device {i}: {e}")
            p.terminate()
        except ImportError:
             print("PyAudio not installed in get_input_devices")
        except Exception as e:
            print(f"Error in get_input_devices: {e}")
        return devices
