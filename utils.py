import random
import string
import os
import json
from datetime import datetime, timedelta
import re
from typing import Dict, List, Optional

def generate_password(length: int = 12) -> str:
    """生成随机密码"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def get_container_name(container_id: int) -> str:
    """根据容器ID生成容器名称"""
    from config import CONTAINER_NAME_FORMAT
    return CONTAINER_NAME_FORMAT.format(id=container_id)

def get_username(username: str) -> str:
    """根据用户名生成实例用户名"""
    from config import USERNAME_FORMAT
    return USERNAME_FORMAT.format(username=username)

def validate_domain(domain: str) -> bool:
    """验证域名格式"""
    pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, domain))

def calculate_expiry(days: int = 5, from_date: Optional[datetime] = None) -> str:
    """计算过期时间"""
    if from_date is None:
        from_date = datetime.utcnow()
    expiry = from_date + timedelta(days=days)
    return expiry.isoformat() + 'Z'

def ensure_data_dir(container_id: int) -> str:
    """确保数据目录存在"""
    from config import DATA_DIR
    # 获取当前工作目录的绝对路径
    base_dir = os.path.abspath(os.getcwd())
    # 构建数据目录的绝对路径
    data_dir = os.path.join(base_dir, DATA_DIR.lstrip('./'), str(container_id))
    # 创建目录
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

def load_config() -> Dict:
    """加载配置文件"""
    try:
        with open('containers.json', 'r') as f:
            return json.loads(f.read())
    except FileNotFoundError:
        return {
            'containers': {},
            'next_id': 1,
            'max_machines': 30,
            'used_ports': []
        }

def save_config(config: Dict) -> None:
    """保存配置文件"""
    with open('containers.json', 'w') as f:
        json.dump(config, f, indent=2)

def get_container_ports(container_id: int) -> Dict[str, int]:
    """获取容器端口映射"""
    from config import BASE_HTTP_PORT, SSH_PORT
    return {
        'http_port': BASE_HTTP_PORT + container_id,  # 每个用户独立的Web端口
        'ssh_port': SSH_PORT,  # 所有用户共用的SSH端口
        'ftp_port': SSH_PORT   # 所有用户共用的FTP端口
    }

def validate_user_container(config: Dict, container_id: str, user_id: str) -> bool:
    """验证容器是否属于用户"""
    container_info = config['containers'].get(container_id)
    return bool(container_info and container_info.get('user_id') == user_id)

def get_container_type(container_info: Dict) -> str:
    """获取容器类型"""
    return container_info.get('type', 'base')

def format_container_info(container_info: Dict) -> Dict:
    """格式化容器信息用于显示"""
    info = container_info.copy()
    # 移除敏感信息
    info.pop('password', None)
    # 格式化日期
    for date_field in ['created_at', 'expires_at']:
        if date_field in info:
            date_str = info[date_field].rstrip('Z').split('.')[0]
            date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S')
            info[date_field] = date.strftime('%Y-%m-%d %H:%M:%S')
    return info

def calculate_machine_stats(config: Dict) -> Dict:
    """计算机器统计信息"""
    from config import MAX_MACHINES
    total_machines = len(config['containers'])
    return {
        'total': total_machines,
        'max': MAX_MACHINES,
        'percentage': (total_machines / MAX_MACHINES) * 100
    }

def get_remaining_time(expires_at: str) -> Dict[str, int]:
    """计算剩余时间，返回天数和小时数"""
    expires_at_str = expires_at.rstrip('Z').split('.')[0]
    expires_at = datetime.strptime(expires_at_str, '%Y-%m-%dT%H:%M:%S')
    now = datetime.utcnow()
    time_delta = expires_at - now
    days = time_delta.days
    hours = time_delta.seconds // 3600
    return {
        'days': days,
        'hours': hours,
        'total_hours': days * 24 + hours
    }
