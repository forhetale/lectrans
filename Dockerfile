# LecTrans Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建 sessions 目录
RUN mkdir -p ~/.lectrans/sessions

# 暴露端口
EXPOSE 8501

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 启动命令
CMD ["streamlit", "run", "ui/app.py", \
     "--server.headless", "true", \
     "--server.port", "8501", \
     "--theme.base", "dark"]
