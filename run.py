#!/usr/bin/env python3
"""
LecTrans - 实时课堂翻译工具
启动脚本
"""

import sys
import subprocess
from pathlib import Path


def check_dependencies():
    """检查依赖"""
    required = [
        'streamlit',
        'openai',
        'groq',
        'pyaudio',
        'pyyaml',
        'python-dotenv',
    ]
    
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    return missing


def install_dependencies():
    """安装依赖"""
    print("Installing dependencies...")
    subprocess.run([
        sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
    ], check=True)


def main():
    """主函数"""
    # 获取项目根目录
    root_dir = Path(__file__).parent
    
    # 检查依赖
    missing = check_dependencies()
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        response = input("Install now? (y/n): ")
        
        if response.lower() == 'y':
            install_dependencies()
        else:
            print("Please install dependencies manually:")
            print(f"  pip install -r {root_dir / 'requirements.txt'}")
            sys.exit(1)
    
    # 启动 Streamlit
    app_path = root_dir / "ui" / "app.py"
    
    print("\n" + "=" * 50)
    print("🎓 LecTrans - 实时课堂翻译工具")
    print("=" * 50)
    print(f"\nStarting server...")
    print(f"Open http://localhost:8501 in your browser\n")
    
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.headless", "true",
        "--theme.base", "dark",
    ])


if __name__ == "__main__":
    main()
