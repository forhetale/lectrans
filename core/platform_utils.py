"""
LecTrans 跨平台文件操作工具

替代直接使用 os.startfile / explorer 等 Windows 专属调用。
"""

import subprocess
import sys
from pathlib import Path

from core.logger import get_logger

logger = get_logger(__name__)


def open_path(path: str) -> bool:
    """使用系统默认程序打开文件"""
    target = str(path)
    try:
        if sys.platform.startswith("win"):
            import os

            os.startfile(target)  # noqa: S606 - Windows 专用
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", target])
            return True
        subprocess.Popen(["xdg-open", target])
        return True
    except Exception as e:
        logger.error("打开文件失败 %s: %s", target, e)
        return False


def reveal_in_folder(path: str) -> bool:
    """在系统文件管理器中定位文件"""
    target = Path(path)
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", "/select,", str(target.resolve())])
            return True
        if sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(target.resolve())])
            return True
        subprocess.Popen(["xdg-open", str(target.resolve().parent)])
        return True
    except Exception as e:
        logger.error("定位文件失败 %s: %s", path, e)
        return False
