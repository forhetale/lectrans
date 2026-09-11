"""配置模块测试"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
from config import AppConfig


class TestAppConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._orig = (config.CONFIG_DIR, config.CONFIG_FILE)
        config.CONFIG_DIR = Path(self.tmp.name)
        config.CONFIG_FILE = config.CONFIG_DIR / "config.json"

        self._patchers = [
            patch.object(config, "_save_secret", return_value=False),
            patch.object(config, "_load_secret", return_value=""),
        ]
        for p in self._patchers:
            p.start()

    def tearDown(self):
        for p in self._patchers:
            p.stop()
        config.CONFIG_DIR, config.CONFIG_FILE = self._orig
        self.tmp.cleanup()

    def test_defaults(self):
        cfg = AppConfig()
        self.assertEqual(cfg.asr_engine, "local")
        self.assertEqual(cfg.sample_rate, 16000)
        self.assertEqual(cfg.llm_model, "mimo-v2.5-pro")
        self.assertEqual(cfg.energy_threshold, 300)
        self.assertEqual(cfg.max_utterance_seconds, 20.0)
        self.assertEqual(cfg.translation_context_size, 5)

    def test_is_configured_local_requires_mimo_key(self):
        cfg = AppConfig()
        self.assertFalse(cfg.is_configured)
        cfg.api_key = "key"
        self.assertTrue(cfg.is_configured)

    def test_is_configured_azure_requires_both_keys(self):
        cfg = AppConfig()
        cfg.asr_engine = "azure"
        cfg.api_key = "mimo"
        self.assertFalse(cfg.is_configured)
        cfg.azure_key = "azure"
        self.assertTrue(cfg.is_configured)

    def test_save_load_roundtrip(self):
        cfg = AppConfig()
        cfg.api_key = "test-key"
        cfg.font_size = 16
        cfg.energy_threshold = 450
        cfg.save()
        self.assertTrue(config.CONFIG_FILE.exists())

        loaded = AppConfig()
        self.assertEqual(loaded.api_key, "test-key")
        self.assertEqual(loaded.font_size, 16)
        self.assertEqual(loaded.energy_threshold, 450)

    def test_env_override(self):
        with patch.dict(os.environ, {"LECTRANS_API_KEY": "env-key", "LECTRANS_LLM_MODEL": "env-model"}):
            cfg = AppConfig()
        self.assertEqual(cfg.api_key, "env-key")
        self.assertEqual(cfg.llm_model, "env-model")

    def test_invalid_env_value_ignored(self):
        with patch.dict(os.environ, {"LECTRANS_FONT_SIZE": "not-a-number"}):
            cfg = AppConfig()
        self.assertEqual(cfg.font_size, 13)

    def test_corrupted_config_file_ignored(self):
        config.CONFIG_FILE.write_text("{ not valid json", encoding="utf-8")
        cfg = AppConfig()
        self.assertEqual(cfg.asr_engine, "local")


if __name__ == "__main__":
    unittest.main()
