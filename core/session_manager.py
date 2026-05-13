"""
LecTrans 会话管理模块
支持自动保存、历史浏览、录音文件关联
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from config import SESSIONS_DIR, RECORDINGS_DIR


class TranscriptEntry:
    """单条转录记录"""

    def __init__(self, korean: str, chinese: str, timestamp: datetime = None):
        self.timestamp = timestamp or datetime.now()
        self.korean = korean
        self.chinese = chinese

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "korean": self.korean,
            "chinese": self.chinese,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TranscriptEntry":
        return cls(
            korean=data["korean"],
            chinese=data["chinese"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


class SessionManager:
    """会话管理器"""

    def __init__(self):
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

    # -------------------- 保存 --------------------

    def save_session(
        self,
        session_id: str,
        transcripts: List[TranscriptEntry],
        summary: str = "",
        recording_path: str = "",
        start_time: datetime = None,
        end_time: datetime = None,
    ) -> str:
        """保存会话到 JSON 文件，返回文件路径"""
        filepath = SESSIONS_DIR / f"{session_id}.json"
        data = {
            "session_id": session_id,
            "start_time": start_time.isoformat() if start_time else "",
            "end_time": end_time.isoformat() if end_time else "",
            "total_entries": len(transcripts),
            "recording_path": recording_path,
            "summary": summary,
            "transcripts": [t.to_dict() for t in transcripts],
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return str(filepath)

    # -------------------- 查询 --------------------

    def list_sessions(self) -> List[dict]:
        """列出所有历史会话（摘要信息），按时间倒序"""
        sessions = []
        for fp in SESSIONS_DIR.glob("*.json"):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                sessions.append({
                    "session_id": data["session_id"],
                    "start_time": data.get("start_time", ""),
                    "total_entries": data.get("total_entries", 0),
                    "recording_path": data.get("recording_path", ""),
                    "filepath": str(fp),
                })
            except Exception:
                continue
        sessions.sort(key=lambda s: s["start_time"], reverse=True)
        return sessions

    def load_session(self, session_id: str) -> Optional[dict]:
        """加载会话完整数据"""
        filepath = SESSIONS_DIR / f"{session_id}.json"
        if not filepath.exists():
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def delete_session(self, session_id: str):
        """删除会话及关联录音"""
        filepath = SESSIONS_DIR / f"{session_id}.json"

        # 删除关联录音
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                rec_path = data.get("recording_path", "")
                if rec_path:
                    p = Path(rec_path)
                    if p.exists():
                        p.unlink()
            except Exception:
                pass
            filepath.unlink()

    # -------------------- 导出 --------------------

    def export_markdown(self, session_id: str, output_path: str = None) -> str:
        """导出会话为 Markdown 文本"""
        data = self.load_session(session_id)
        if not data:
            return ""

        lines = [
            "# LecTrans 课堂笔记\n",
            f"**日期**: {data.get('start_time', '未知')}\n",
            "---\n",
        ]
        for t in data.get("transcripts", []):
            ts = t.get("timestamp", "")
            if ts:
                try:
                    ts = datetime.fromisoformat(ts).strftime("%H:%M:%S")
                except Exception:
                    pass
            lines.append(f"### [{ts}]")
            lines.append(f"**韩语**: {t['korean']}\n")
            lines.append(f"**中文**: {t['chinese']}\n")
            lines.append("---\n")

        summary = data.get("summary", "")
        if summary:
            lines.append(f"\n## 总结\n\n{summary}")

        markdown = "\n".join(lines)

        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, 'w', encoding='utf-8') as f:
                f.write(markdown)

        return markdown
