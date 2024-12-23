#!/bin/bash

# 退出时的错误处理
set -e

# 检查 Python 虚拟环境
VENV_DIR="venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    python3 -m venv $VENV_DIR
fi

# 激活虚拟环境
source $VENV_DIR/bin/activate

# 设置环境变量
export PYTHONUNBUFFERED=1
if [ -z "$FLASK_ENV" ]; then
    export FLASK_ENV=production
fi

# 安装依赖
echo "安装项目依赖..."
pip install --upgrade pip
pip install -r requirements.txt
pip install eventlet gunicorn

# 创建日志目录
LOG_DIR="logs"
if [ ! -d "$LOG_DIR" ]; then
    mkdir -p $LOG_DIR
fi

# 启动 gunicorn
echo "启动 Gunicorn 服务器..."
exec gunicorn "app:create_app()" \
    --worker-class eventlet \
    --workers 1 \
    --bind 0.0.0.0:8181 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --capture-output \
    --enable-stdio-inheritance \
    --log-syslog \
    --pid gunicorn.pid \
    --preload \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --reload

# 注意：这段代码不会被执行，因为 exec 会替换当前进程
deactivate
