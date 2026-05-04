#!/bin/bash
# LecTrans 安装脚本

set -e

echo "=========================================="
echo "🎓 LecTrans - 实时课堂翻译工具"
echo "=========================================="
echo ""

# 检查 Python 版本
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# 创建虚拟环境
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# 激活虚拟环境
echo "Activating virtual environment..."
source venv/bin/activate

# 升级 pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# 安装依赖
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# 创建 .env 文件
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys"
fi

# 创建 sessions 目录
mkdir -p ~/.lectrans/sessions

echo ""
echo "=========================================="
echo "✅ Installation complete!"
echo "=========================================="
echo ""
echo "To start LecTrans:"
echo ""
echo "  1. Edit .env and add your API keys"
echo "  2. Run: source venv/bin/activate"
echo "  3. Run: python run.py"
echo ""
echo "Or simply run:"
echo "  ./start.sh"
echo ""
