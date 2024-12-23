from typing import Dict, List, Optional, Tuple
from datetime import datetime
import subprocess
import json
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

    def create_container(self, container_id: int, username: str, password: str, container_type: str = 'base', user_id: str = None) -> Tuple[str, int]:
        """创建新容器,返回(容器名称, 实际使用的ID)"""
        while True:
            container_name = get_container_name(container_id)
            # 检查容器是否已存在
            try:
                subprocess.run(['sudo', 'docker', 'inspect', container_name], 
                             check=True, capture_output=True)
                # 容器已存在,尝试下一个ID
                container_id += 1
                continue
            except subprocess.CalledProcessError:
                # 容器不存在,可以使用这个名称
                break
                
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
            
            # 将bashecho内容写入临时文件
            with open('/tmp/container_bashecho', 'w') as f:
                f.write(bashecho_content)
            
            # 复制文件到容器
            subprocess.run(['sudo', 'docker', 'cp', '/tmp/container_bashecho', f'{container_name}:/tmp/bashecho'], check=True)
            
            # 添加到.bashrc
            subprocess.run(['sudo', 'docker', 'exec', container_name, 'bash', '-c', 'echo "\n# DotMachine welcome message" >> /home/$CONTAINER_USER/.bashrc'], check=True)
            subprocess.run(['sudo', 'docker', 'exec', container_name, 'bash', '-c', 'cat /tmp/bashecho >> /home/$CONTAINER_USER/.bashrc'], check=True)
            subprocess.run(['sudo', 'docker', 'exec', container_name, 'rm', '/tmp/bashecho'], check=True)
            
            # 清理本地临时文件
            os.remove('/tmp/container_bashecho')
        
        return container_name, container_id

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
            
    def get_container_status(self, container_name: str) -> Dict:
        """获取容器状态信息"""
        try:
            # 获取容器运行状态
            inspect_result = subprocess.run(
                ['sudo', 'docker', 'inspect', container_name],
                check=True, capture_output=True, text=True
            )
            container_info = json.loads(inspect_result.stdout)[0]
            running = container_info['State']['Running']
            
            if not running:
                return {
                    'status': 'stopped',
                    'cpu_usage': 0,
                    'memory_usage': 0,
                    'memory_limit': 0,
                    'disk_usage': 0,
                    'disk_limit': 0
                }
            
            # 获取容器统计信息
            stats_result = subprocess.run(
                ['sudo', 'docker', 'stats', container_name, '--no-stream', '--format', '{{json .}}'],
                check=True, capture_output=True, text=True
            )
            stats = json.loads(stats_result.stdout)
            
            # 获取容器磁盘使用情况
            df_result = subprocess.run(
                ['sudo', 'docker', 'exec', container_name, 'df', '-B1', '/data'],
                check=True, capture_output=True, text=True
            )
            df_lines = df_result.stdout.strip().split('\n')
            disk_info = df_lines[1].split()
            disk_total = int(disk_info[1])
            disk_used = int(disk_info[2])
            
            return {
                'status': 'running',
                'cpu_usage': float(stats['CPUPerc'].strip('%')),
                'memory_usage': int(stats['MemUsage'].split('/')[0].strip().replace('MiB', '')) * 1024 * 1024,
                'memory_limit': int(stats['MemUsage'].split('/')[1].strip().replace('MiB', '')) * 1024 * 1024,
                'disk_usage': disk_used,
                'disk_limit': disk_total
            }
            
        except subprocess.CalledProcessError as e:
            return {
                'status': 'error',
                'error': str(e)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': f'获取容器状态失败: {str(e)}'
            }

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
                raise ValueError("用户已经创建了一个实例")

        # 生成容器信息
        container_id = config['next_id']
        original_id = container_id  # 保存原始ID用于后续更新
        from utils import generate_password
        password = generate_password()
        
        # 创建容器并获取实际使用的容器名称和ID
        container_name, actual_id = self.docker.create_container(
            container_id=container_id,
            username=username,
            password=password,
            container_type=container_type,
            user_id=user_id
        )
        
        # 更新配置
        ports = get_container_ports(actual_id)
        container_info = {
            'name': container_name,  # 使用实际返回的容器名称
            'username': username,
            'password': password,
            'user_id': user_id,
            'type': container_type,
            **ports,
            'websites': [],
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'expires_at': calculate_expiry()
        }
        
        config['containers'][str(actual_id)] = container_info
        config['next_id'] = actual_id + 1
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
