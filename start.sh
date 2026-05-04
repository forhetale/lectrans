#!/bin/bash
# LecTrans 启动脚本

set -e

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Run ./install.sh first."
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 启动应用
echo "🎓 Starting LecTrans..."
python run.py
