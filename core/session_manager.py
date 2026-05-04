"""
LecTrans 会话管理模块
"""

from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import json
import yaml


@dataclass
class TranscriptEntry:
    """转录条目"""
    id: int
    timestamp: datetime
    korean_text: str
    chinese_text: str
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "korean": self.korean_text,
            "chinese": self.chinese_text
        }


@dataclass
class SessionState:
    """会话状态"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    
    # 转录记录
    transcripts: List[TranscriptEntry] = field(default_factory=list)
    
    # 总结
    summary: Optional[str] = None
    
    # 状态标志
    is_recording: bool = False
    is_connected: bool = False
    
    # 统计
    total_entries: int = 0
    total_duration: float = 0.0  # 秒
    
    def add_transcript(self, korean: str, chinese: str) -> TranscriptEntry:
        """添加转录条目"""
        entry = TranscriptEntry(
            id=len(self.transcripts) + 1,
            timestamp=datetime.now(),
            korean_text=korean,
            chinese_text=chinese
        )
        self.transcripts.append(entry)
        self.total_entries = len(self.transcripts)
        return entry
    
    def get_full_transcript(self) -> str:
        """获取完整转录文本"""
        lines = []
        for entry in self.transcripts:
            lines.append(f"[{entry.timestamp.strftime('%H:%M:%S')}] {entry.korean_text}")
        return "\n".join(lines)
    
    def get_bilingual_transcript(self) -> str:
        """获取双语转录文本"""
        lines = []
        for entry in self.transcripts:
            lines.append(f"[{entry.timestamp.strftime('%H:%M:%S')}]")
            lines.append(f"韩: {entry.korean_text}")
            lines.append(f"中: {entry.chinese_text}")
            lines.append("")
        return "\n".join(lines)


class SessionManager:
    """会话管理器"""
    
    def __init__(self, storage_dir: str = None):
        self.storage_dir = Path(storage_dir or Path.home() / ".lectrans" / "sessions")
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[SessionState] = None
    
    def start_session(self) -> SessionState:
        """开始新会话"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.current_session = SessionState(
            session_id=session_id,
            start_time=datetime.now()
        )
        
        return self.current_session
    
    def end_session(self):
        """结束当前会话"""
        if self.current_session:
            self.current_session.end_time = datetime.now()
            
            # 计算总时长
            if self.current_session.end_time and self.current_session.start_time:
                delta = self.current_session.end_time - self.current_session.start_time
                self.current_session.total_duration = delta.total_seconds()
    
    def save_session(self, filepath: str = None) -> str:
        """保存会话"""
        if not self.current_session:
            raise ValueError("No active session")
        
        # 确定文件路径
        if filepath:
            save_path = Path(filepath)
        else:
            save_path = self.storage_dir / f"session_{self.current_session.session_id}.yaml"
        
        # 构建数据
        data = {
            "session_id": self.current_session.session_id,
            "start_time": self.current_session.start_time.isoformat(),
            "end_time": self.current_session.end_time.isoformat() if self.current_session.end_time else None,
            "total_entries": self.current_session.total_entries,
            "total_duration": self.current_session.total_duration,
            "transcripts": [t.to_dict() for t in self.current_session.transcripts],
            "summary": self.current_session.summary
        }
        
        # 保存
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        return str(save_path)
    
    def load_session(self, filepath: str) -> SessionState:
        """加载会话"""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # 创建会话
        session = SessionState(
            session_id=data['session_id'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']) if data.get('end_time') else None,
            total_entries=data.get('total_entries', 0),
            total_duration=data.get('total_duration', 0),
            summary=data.get('summary')
        )
        
        # 加载转录记录
        for t in data.get('transcripts', []):
            entry = TranscriptEntry(
                id=t['id'],
                timestamp=datetime.fromisoformat(t['timestamp']),
                korean_text=t['korean'],
                chinese_text=t['chinese']
            )
            session.transcripts.append(entry)
        
        return session
    
    def list_sessions(self) -> List[dict]:
        """列出所有会话"""
        sessions = []
        
        for filepath in sorted(self.storage_dir.glob("session_*.yaml")):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                
                sessions.append({
                    "session_id": data['session_id'],
                    "start_time": data['start_time'],
                    "total_entries": data.get('total_entries', 0),
                    "filepath": str(filepath)
                })
            except Exception:
                continue
        
        return sessions
    
    def export_markdown(self, filepath: str = None) -> str:
        """导出为 Markdown"""
        if not self.current_session:
            raise ValueError("No active session")
        
        session = self.current_session
        
        # 构建 Markdown
        lines = [
            f"# LecTrans 课堂笔记",
            f"",
            f"**日期**: {session.start_time.strftime('%Y-%m-%d %H:%M')}",
            f"**时长**: {session.total_duration / 60:.1f} 分钟",
            f"**条目**: {session.total_entries} 条",
            f"",
            f"---",
            f"",
            f"## 📝 转录内容",
            f""
        ]
        
        for entry in session.transcripts:
            lines.append(f"### [{entry.timestamp.strftime('%H:%M:%S')}]")
            lines.append(f"")
            lines.append(f"**🇰🇷 한국어**: {entry.korean_text}")
            lines.append(f"")
            lines.append(f"**🇨🇳 中文**: {entry.chinese_text}")
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")
        
        if session.summary:
            lines.append(f"## 📚 课堂总结")
            lines.append(f"")
            lines.append(session.summary)
        
        markdown = "\n".join(lines)
        
        # 保存到文件
        if filepath:
            save_path = Path(filepath)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(markdown)
        
        return markdown
