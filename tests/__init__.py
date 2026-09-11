"""
测试包初始化

- 将配置目录重定向到临时目录，避免污染真实 ~/.lectrans
- 在导入任何应用模块之前设置 LECTRANS_HOME
"""

import atexit
import os
import shutil
import tempfile

_created_here = "LECTRANS_HOME" not in os.environ
if _created_here:
    os.environ["LECTRANS_HOME"] = tempfile.mkdtemp(prefix="lectrans-test-")

_TEST_HOME = os.environ["LECTRANS_HOME"]


def _cleanup():
    if _created_here:
        shutil.rmtree(_TEST_HOME, ignore_errors=True)


atexit.register(_cleanup)
