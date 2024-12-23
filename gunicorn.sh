#!/bin/bash

# 安装依赖
pip install -r requirements.txt

# 启动 gunicorn
gunicorn webui:app \
    --workers 3 \
    --bind 0.0.0.0:8181 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
