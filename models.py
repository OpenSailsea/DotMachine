from typing import Dict, List, Optional, Tuple
from datetime import datetime
import subprocess
from config import CONTAINER_LIMITS
import random
import os
from utils import (
    get_container_name,
    get_container_ports,
    ensure_data_dir,
    calculate_expiry,
    load_config,
    save_config,
    validate_user_container
)

class DockerManager:
    """Docker容器管理类"""
    def __init__(self):
        pass

    def create_container(self, container_id: int, username: str, password: str, container_type: str = 'base', user_id: str = None) -> str:
        """创建新容器"""
        container_name = get_container_name(container_id)
        image_name = f'dotmachine-{container_type}'
        ports = get_container_ports(container_id)
        data_dir = ensure_data_dir(container_id)

        # 确保镜像存在
        try:
            subprocess.run(['sudo', 'docker', 'image', 'inspect', image_name], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            subprocess.run(['sudo', 'docker', 'build', '-t', image_name, '-f', f'Dockerfile.{container_type}', '.'], check=True)

        # 创建并启动容器
        cmd = [
            'sudo', 'docker', 'run', '-d',
            '--name', container_name,
            '--privileged',  # 添加特权模式
            '--cap-add=NET_ADMIN',  # 添加网络管理权限
            '--cap-add=NET_RAW',    # 添加原始网络权限
            '-p', f'{ports["ssh_port"]}:22',
            '-p', f'{ports["ftp_port"]}:21',
            '-p', f'{ports["http_port"]}:9000',
            '-v', f'{os.path.abspath(data_dir)}:/data:rw',
            '--cpu-period', str(CONTAINER_LIMITS["cpu_period"]),
            '--cpu-quota', str(CONTAINER_LIMITS["cpu_quota"]),
            '--memory', CONTAINER_LIMITS["mem_limit"].replace('m', 'M'),
            '-e', f'CONTAINER_USER={username}',
            '-e', f'CONTAINER_PASSWORD={password}',
            image_name
        ]

        subprocess.run(cmd, check=True)

        # 在容器中创建用户
        subprocess.run(['sudo', 'docker', 'exec', container_name, '/usr/local/bin/create_user.sh', username, password], check=True)
        
        # 修改用户的.bashrc
        if os.path.exists('.bashecho'):
            with open('.bashecho', 'r') as f:
                bashecho_content = f.read()
            
            # 创建临时文件并添加到.bashrc
            subprocess.run(['sudo', 'docker', 'exec', container_name, 'sh', '-c', f'echo "{bashecho_content}" > /tmp/bashecho'], check=True)
            subprocess.run(['sudo', 'docker', 'exec', container_name, 'sh', '-c', f'echo "\n# DotMachine welcome message" >> /home/{username}/.bashrc'], check=True)
            subprocess.run(['sudo', 'docker', 'exec', container_name, 'sh', '-c', f'cat /tmp/bashecho >> /home/{username}/.bashrc'], check=True)
            subprocess.run(['sudo', 'docker', 'exec', container_name, 'rm', '/tmp/bashecho'], check=True)
        
        return container_name

    def remove_container(self, container_name: str) -> None:
        """删除容器"""
        try:
            subprocess.run(['sudo', 'docker', 'stop', container_name], check=True)
            subprocess.run(['sudo', 'docker', 'rm', container_name], check=True)
        except subprocess.CalledProcessError:
            pass

    def get_container(self, container_name: str) -> Optional[str]:
        """获取容器实例"""
        try:
            subprocess.run(['sudo', 'docker', 'inspect', container_name], check=True, capture_output=True)
            return container_name
        except subprocess.CalledProcessError:
            return None

class ContainerManager:
    """容器管理类"""
    def __init__(self):
        self.docker = DockerManager()

    def create_container(self, user_id: str, username: str, container_type: str = 'base') -> Tuple[Dict, str]:
        """创建新容器并更新配置"""
        config = load_config()
        
        # 检查用户是否已有容器
        for info in config['containers'].values():
            if info.get('user_id') == user_id:
                raise ValueError("用户已经创建了一个VPS")

        # 生成容器信息
        container_id = config['next_id']
        from utils import generate_password
        password = generate_password()
        
        # 创建容器
        container = self.docker.create_container(
            container_id=container_id,
            username=username,
            password=password,
            container_type=container_type,
            user_id=user_id
        )
        
        # 更新配置
        ports = get_container_ports(container_id)
        container_info = {
            'name': get_container_name(container_id),
            'username': username,
            'password': password,
            'user_id': user_id,
            'type': container_type,
            **ports,
            'websites': [],
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'expires_at': calculate_expiry()
        }
        
        config['containers'][str(container_id)] = container_info
        config['next_id'] = container_id + 1
        save_config(config)
        
        return container_info, password

    def remove_container(self, container_id: str, user_id: str) -> None:
        """删除容器并更新配置"""
        config = load_config()
        
        # 验证容器属于用户
        container_info = config['containers'].get(container_id)
        if not container_info or container_info.get('user_id') != user_id:
            raise ValueError("无权操作此容器")
        
        # 删除容器
        container_name = get_container_name(int(container_id))
        self.docker.remove_container(container_name)
        
        # 更新配置
        del config['containers'][container_id]
        save_config(config)
