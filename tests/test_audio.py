"""音频录制模块测试（不依赖真实麦克风）"""

import tempfile
import unittest
import wave
from pathlib import Path

from core.audio_recorder import AudioRecorder


class TestAudioFiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_wav_produces_valid_riff(self):
        path = self.dir / "sample.wav"
        data = b"\x00\x00" * 16000  # 1 秒 16-bit 单声道静音

        result = AudioRecorder.save_wav(str(path), data, sample_rate=16000)

        self.assertEqual(result, str(path))
        with wave.open(str(path), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), 16000)
            self.assertEqual(wf.getnframes(), 16000)

    def test_save_mp3_returns_existing_path(self):
        """无论 MP3 转码是否可用（pydub/ffmpeg 可能缺失），都必须返回真实存在的文件"""
        path = self.dir / "sample.mp3"
        result = AudioRecorder.save_mp3(str(path), b"\x00\x00" * 16000, sample_rate=16000)

        self.assertTrue(result)
        self.assertTrue(Path(result).exists())
        self.assertIn(Path(result).suffix.lower(), {".mp3", ".wav"})

    def test_convert_missing_wav_returns_empty(self):
        result = AudioRecorder.convert_wav_to_mp3(
            str(self.dir / "missing.wav"), str(self.dir / "out.mp3")
        )
        self.assertEqual(result, "")


class TestConsumerDispatch(unittest.TestCase):
    def test_dispatch_drops_oldest_when_full(self):
        recorder = AudioRecorder(consumer_queue_size=2)
        q = recorder.subscribe()
        recorder._dispatch(b"1")
        recorder._dispatch(b"2")
        recorder._dispatch(b"3")

        self.assertEqual(q.get_nowait(), b"2")
        self.assertEqual(q.get_nowait(), b"3")

    def test_dispatch_to_multiple_consumers(self):
        recorder = AudioRecorder()
        q1 = recorder.subscribe()
        q2 = recorder.subscribe()
        recorder._dispatch(b"data")

        self.assertEqual(q1.get_nowait(), b"data")
        self.assertEqual(q2.get_nowait(), b"data")

    def test_unsubscribe_stops_delivery(self):
        recorder = AudioRecorder()
        q = recorder.subscribe()
        recorder.unsubscribe(q)
        recorder._dispatch(b"data")
        self.assertTrue(q.empty())

    def test_duration_and_size_track_bytes(self):
        recorder = AudioRecorder(sample_rate=16000)
        recorder._recorded_bytes = 32000  # 1 秒
        self.assertEqual(recorder.duration(), 1.0)
        self.assertEqual(recorder.recording_size(), 32000)


if __name__ == "__main__":
    unittest.main()
