#!/bin/bash

# 安装依赖
pip install -r requirements.txt

# 安装eventlet
pip install eventlet

# 启动 gunicorn
gunicorn app:socketio \
    --worker-class eventlet \
    --workers 1 \
    --bind 0.0.0.0:8181 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
