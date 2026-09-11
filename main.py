"""
LecTrans - 实时课堂翻译工具

桌面应用入口：加载 .env、初始化日志，然后启动 tkinter 主窗口。
"""

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - 可选依赖
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(Path(__file__).parent / ".env")

from core.logger import setup_logging  # noqa: E402
from ui.app import LecTransApp  # noqa: E402


def main():
    setup_logging()
    app = LecTransApp()
    app.run()


if __name__ == "__main__":
    main()
