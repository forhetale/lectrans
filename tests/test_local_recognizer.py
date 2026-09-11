"""本地识别器 VAD 辅助逻辑测试（需要 numpy，缺失时跳过）"""

import unittest

from core import local_recognizer
from core.local_recognizer import LocalWhisperRecognizer


@unittest.skipIf(local_recognizer.np is None, "numpy 未安装")
class TestVadHelpers(unittest.TestCase):
    def setUp(self):
        self.recognizer = LocalWhisperRecognizer(energy_threshold=300, vad_factor=3.0)

    def test_rms_silence_is_zero(self):
        silence = local_recognizer.np.zeros(1024, dtype=local_recognizer.np.int16)
        self.assertEqual(self.recognizer._rms(silence), 0.0)

    def test_rms_empty_is_zero(self):
        empty = local_recognizer.np.array([], dtype=local_recognizer.np.int16)
        self.assertEqual(self.recognizer._rms(empty), 0.0)

    def test_threshold_without_noise_floor(self):
        self.assertEqual(self.recognizer._threshold(None), 300.0)

    def test_threshold_uses_max_of_base_and_noise(self):
        self.assertEqual(self.recognizer._threshold(50.0), 300.0)   # 底噪 * 3 < 基准
        self.assertEqual(self.recognizer._threshold(200.0), 600.0)  # 底噪 * 3 > 基准

    def test_start_reports_error_when_dependency_missing(self):
        errors = []
        self.recognizer.on_error = errors.append
        if local_recognizer.WhisperModel is None:
            ok = self.recognizer.start_continuous_recognition(None)
            self.assertFalse(ok)
            self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
