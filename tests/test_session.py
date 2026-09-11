"""会话管理测试"""

import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import core.session_manager as sm
from core.session_manager import SessionManager, TranscriptEntry


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._orig = (sm.SESSIONS_DIR, sm.RECORDINGS_DIR)
        sm.SESSIONS_DIR = Path(self.tmp.name) / "sessions"
        sm.RECORDINGS_DIR = Path(self.tmp.name) / "recordings"
        self.manager = SessionManager()
        self.start = datetime.now()
        self.entries = [
            TranscriptEntry("안녕하세요", "你好", timestamp=self.start),
            TranscriptEntry("자료구조", "数据结构", timestamp=self.start + timedelta(seconds=5)),
        ]

    def tearDown(self):
        sm.SESSIONS_DIR, sm.RECORDINGS_DIR = self._orig
        self.tmp.cleanup()

    def test_save_and_load_session(self):
        path = self.manager.save_session(
            "20260101_090000",
            self.entries,
            summary="总结内容",
            start_time=self.start,
            end_time=self.start + timedelta(minutes=1),
        )
        self.assertTrue(Path(path).exists())

        data = self.manager.load_session("20260101_090000")
        self.assertEqual(data["total_entries"], 2)
        self.assertEqual(data["transcripts"][0]["korean"], "안녕하세요")
        self.assertEqual(data["summary"], "总结内容")
        self.assertEqual(data["end_time"], (self.start + timedelta(minutes=1)).isoformat())

    def test_list_sessions_sorted_desc(self):
        self.manager.save_session("old", self.entries, start_time=self.start - timedelta(hours=1))
        self.manager.save_session("new", self.entries, start_time=self.start)

        sessions = self.manager.list_sessions()
        self.assertEqual([s["session_id"] for s in sessions], ["new", "old"])

    def test_list_sessions_skips_corrupted_file(self):
        sm.SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        (sm.SESSIONS_DIR / "broken.json").write_text("{ not json", encoding="utf-8")
        self.manager.save_session("ok", self.entries, start_time=self.start)

        sessions = self.manager.list_sessions()
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["session_id"], "ok")

    def test_export_markdown(self):
        self.manager.save_session(
            "md", self.entries, summary="## 总结\n要点", start_time=self.start)
        output = Path(self.tmp.name) / "notes.md"

        markdown = self.manager.export_markdown("md", output_path=str(output))

        self.assertIn("LecTrans 课堂笔记", markdown)
        self.assertIn("안녕하세요", markdown)
        self.assertIn("你好", markdown)
        self.assertIn("## 总结", markdown)
        self.assertEqual(output.read_text(encoding="utf-8"), markdown)

    def test_delete_session_removes_recording(self):
        recording = Path(self.tmp.name) / "recording.mp3"
        recording.write_bytes(b"fake")
        self.manager.save_session(
            "del", self.entries, recording_path=str(recording), start_time=self.start)

        self.manager.delete_session("del")

        self.assertIsNone(self.manager.load_session("del"))
        self.assertFalse(recording.exists())

    def test_load_missing_session_returns_none(self):
        self.assertIsNone(self.manager.load_session("no-such-session"))


class TestTranscriptEntry(unittest.TestCase):
    def test_roundtrip_dict(self):
        entry = TranscriptEntry("원문", "译文", timestamp=datetime(2026, 1, 1, 10, 0, 0))
        restored = TranscriptEntry.from_dict(entry.to_dict())
        self.assertEqual(restored.korean, "원문")
        self.assertEqual(restored.chinese, "译文")
        self.assertEqual(restored.timestamp, entry.timestamp)


if __name__ == "__main__":
    unittest.main()
