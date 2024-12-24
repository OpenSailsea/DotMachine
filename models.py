from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import subprocess
import json
from config import CONTAINER_LIMITS, MAX_MACHINES
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

class ContainerWrapper:
    """Docker容器包装类,提供与docker-py兼容的接口"""
    def __init__(self, name: str):
        self.name = name
        
    def exec_run(self, cmd: List[str], **kwargs) -> Any:
        """执行容器命令"""
        full_cmd = ['sudo', 'docker', 'exec', self.name] + cmd
        try:
            result = subprocess.run(full_cmd, check=True, capture_output=True)
            return type('ExecResult', (), {
                'exit_code': result.returncode,
                'output': result.stdout
            })
        except subprocess.CalledProcessError as e:
            return type('ExecResult', (), {
                'exit_code': e.returncode,
                'output': e.stderr
            })

class DockerManager:
    """Docker容器管理类"""
    def __init__(self):
        pass

    def cleanup_docker_network(self):
        """清理Docker网络设置"""
        try:
            # 停止所有容器
            subprocess.run(['sudo', 'docker', 'stop', '$(sudo docker ps -aq)'], 
                         shell=True, check=False)
            # 删除所有容器
            subprocess.run(['sudo', 'docker', 'rm', '$(sudo docker ps -aq)'], 
                         shell=True, check=False)
            # 清理网络
            subprocess.run(['sudo', 'docker', 'network', 'prune', '-f'], 
                         check=True)
            # 重启Docker服务
            subprocess.run(['sudo', 'systemctl', 'restart', 'docker'], 
                         check=True)
        except subprocess.CalledProcessError:
            pass

    def create_container(self, container_id: int, username: str, password: str, container_type: str = 'base', user_id: str = None) -> Tuple[str, int]:
        """创建新容器,返回(容器名称, 实际使用的ID)"""
        try:
            container_name = get_container_name(container_id)
            
            # 检查容器是否已存在
            try:
                subprocess.run(['sudo', 'docker', 'inspect', container_name], 
                             check=True, capture_output=True)
                # 如果容器存在，先删除它
                self.remove_container(container_name)
            except subprocess.CalledProcessError:
                pass  # 容器不存在，可以直接创建
                    
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

            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                # 如果创建失败，尝试清理Docker网络并重试
                self.cleanup_docker_network()
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
            
        except Exception as e:
            # 如果发生任何错误，尝试清理并重新抛出异常
            self.cleanup_docker_network()
            raise e

    def remove_container(self, container_name: str) -> None:
        """删除容器"""
        try:
            subprocess.run(['sudo', 'docker', 'stop', container_name], check=True)
            subprocess.run(['sudo', 'docker', 'rm', container_name], check=True)
        except subprocess.CalledProcessError:
            pass

    def get_container(self, container_name: str) -> Optional[ContainerWrapper]:
        """获取容器实例"""
        try:
            subprocess.run(['sudo', 'docker', 'inspect', container_name], check=True, capture_output=True)
            return ContainerWrapper(container_name)
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
        for cid, info in config['containers'].items():
            if info.get('user_id') == user_id:
                raise ValueError("用户已经创建了一个实例")
                
        # 检查总机器数量是否达到上限
        if len(config['containers']) >= MAX_MACHINES:
            raise ValueError(f"系统已达到最大实例数量限制({MAX_MACHINES})")

        # 查找可用的container_id
        container_id = None
        existing_ids = set(int(cid) for cid in config['containers'].keys())
        
        # 如果next_id已经被使用，找到一个未使用的ID
        if config['next_id'] in existing_ids:
            # 从1开始查找第一个未使用的ID
            for i in range(1, MAX_MACHINES + 1):
                if i not in existing_ids:
                    container_id = i
                    break
            if container_id is None:
                raise ValueError(f"没有可用的容器ID")
        else:
            container_id = config['next_id']
            
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
