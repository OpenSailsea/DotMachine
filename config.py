import os

# OAuth2 配置
CLIENT_ID = "dMqfCRZxCovhobmVxw9E1pKYzdmDCZor"
CLIENT_SECRET = "CMJ8QJPawaV4GTVS9cdRcoCeCc0B7J93"
REDIRECT_URI = "https://panel2.fetdev.me/oauth2/callback"
AUTH_BASE_URL = "https://connect.linux.do/oauth2/authorize"
TOKEN_URL = "https://connect.linux.do/oauth2/token"
USER_INFO_URL = "https://connect.linux.do/api/user"

# Flask配置
SECRET_KEY = os.urandom(24)
DEBUG = True
HOST = '0.0.0.0'
PORT = 8002

# Docker配置
BASE_HTTP_PORT = 5000
BASE_SSH_PORT = 5100
BASE_FTP_PORT = 5200

# 系统配置
MAX_MACHINES = 30
DATA_DIR = "./data/containers"

# 容器资源限制
CONTAINER_LIMITS = {
    'cpu_period': 100000,
    'cpu_quota': 3000,  # 0.03 CPU (30mCPU)
    'mem_limit': '51.2m',
    'storage_size': '3G'
}
