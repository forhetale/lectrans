"""
LecTrans 日志模块

统一日志出口：文件（~/.lectrans/lectrans.log，滚动 1MB x 3）+ 控制台。
窗口化 exe 中若无 stderr，则仅写文件。
"""

import logging
import sys
from logging.handlers import RotatingFileHandler

from config import LOG_FILE

_configured = False


def setup_logging(level: int = logging.INFO):
    """初始化根日志（幂等）"""
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    except Exception:
        pass

    if sys.stderr is not None:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """获取模块日志器"""
    setup_logging()
    return logging.getLogger(name)
