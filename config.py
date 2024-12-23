import os

# OAuth2 配置
CLIENT_ID = "hi3geJYfTotoiR5S62u3rh4W5tSeC5UG"
CLIENT_SECRET = "VMPBVoAfOB5ojkGXRDEtzvDhRLENHpaN"
REDIRECT_URI = "http://localhost:8181/oauth2/callback"
AUTH_BASE_URL = "https://connect.linux.do/oauth2/authorize"
TOKEN_URL = "https://connect.linux.do/oauth2/token"
USER_INFO_URL = "https://connect.linux.do/api/user"

# Flask配置
SECRET_KEY = os.urandom(24)
DEBUG = True
HOST = '0.0.0.0'
PORT = 8181

# Docker配置
BASE_HTTP_PORT = 5000
BASE_SSH_PORT = 5100
BASE_FTP_PORT = 5200

# 系统配置
MAX_MACHINES = 20
DATA_DIR = "./data/containers"

# 容器资源限制
CONTAINER_LIMITS = {
    'cpu_period': 100000,
    'cpu_quota': 3000,  # 0.03 CPU (30mCPU)
    'mem_limit': '51.2m',
    'storage_size': '3G'
}
