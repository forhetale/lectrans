"""核心包导入行为测试（PEP 562 惰性导入）"""

import subprocess
import sys
import unittest
from pathlib import Path

import core

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestLazyImports(unittest.TestCase):
    def test_lightweight_classes_available(self):
        from core import AudioManager, AudioRecorder, MiMoClient, SessionManager, TranscriptEntry

        self.assertTrue(callable(AudioRecorder.save_wav))
        self.assertTrue(callable(AudioManager.get_input_devices))
        self.assertTrue(callable(MiMoClient))
        self.assertTrue(callable(SessionManager))
        self.assertTrue(callable(TranscriptEntry))

    def test_transcription_result_defaults(self):
        from core import TranscriptionResult

        result = TranscriptionResult(text="안녕하세요")
        self.assertEqual(result.text, "안녕하세요")
        self.assertEqual(result.language, "ko")
        self.assertEqual(result.confidence, 0.0)

    def test_unknown_attribute_raises(self):
        with self.assertRaises(AttributeError):
            _ = core.DoesNotExist  # noqa: B018

    def test_azure_sdk_not_required_for_local_use(self):
        """本地模式导入 core 不应触发 azure 模块导入（子进程隔离，避免受测试顺序影响）"""
        code = (
            "import sys\n"
            "import core\n"
            "assert 'core.azure_recognizer' not in sys.modules, 'azure imported eagerly'\n"
            "from core import AudioRecorder, MiMoClient, SessionManager, TranscriptionResult\n"
            "assert 'core.azure_recognizer' not in sys.modules, 'azure imported by lazy access'\n"
            "print('ok')\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(_PROJECT_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok", result.stdout)

    def test_dir_lists_public_names(self):
        names = dir(core)
        for name in core.__all__:
            self.assertIn(name, names)


if __name__ == "__main__":
    unittest.main()
