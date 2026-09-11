"""Azure 识别器辅助逻辑测试（未安装 Azure SDK 时跳过）"""

import json
import unittest

try:
    import azure.cognitiveservices.speech  # noqa: F401

    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False


@unittest.skipUnless(HAS_AZURE, "azure-cognitiveservices-speech 未安装")
class TestAzureConfidence(unittest.TestCase):
    class _FakeResult:
        def __init__(self, payload):
            self.json = payload

    class _FakeEvent:
        def __init__(self, payload):
            self.result = TestAzureConfidence._FakeResult(payload)

    def test_extract_confidence(self):
        from core.azure_recognizer import AzureSpeechRecognizer

        payload = json.dumps({"NBest": [{"Confidence": 0.87}]})
        self.assertAlmostEqual(
            AzureSpeechRecognizer._extract_confidence(self._FakeEvent(payload)), 0.87
        )

    def test_extract_confidence_malformed(self):
        from core.azure_recognizer import AzureSpeechRecognizer

        self.assertEqual(
            AzureSpeechRecognizer._extract_confidence(self._FakeEvent("not json")), 0.0
        )

    def test_extract_confidence_empty_nbest(self):
        from core.azure_recognizer import AzureSpeechRecognizer

        payload = json.dumps({"NBest": []})
        self.assertEqual(
            AzureSpeechRecognizer._extract_confidence(self._FakeEvent(payload)), 0.0
        )


if __name__ == "__main__":
    unittest.main()
