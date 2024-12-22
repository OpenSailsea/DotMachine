#!/usr/bin/env python3
import click
import docker
import json
import os
import random
import string
import subprocess
import sys
from rich.console import Console
from rich.table import Table

console = Console()

def run_docker_command(command, *args, **kwargs):
    """使用sudo运行docker命令"""
    try:
        # 尝试直接运行
        result = subprocess.run(['docker'] + command, 
                              check=True, 
                              capture_output=True,
                              text=True)
        return result.stdout
    except subprocess.CalledProcessError:
        # 如果失败，尝试使用sudo
        try:
            result = subprocess.run(['sudo', 'docker'] + command,
                                  check=True,
                                  capture_output=True,
                                  text=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            console.print(f"错误: Docker命令执行失败: {e}", style="red")
            sys.exit(1)

class DockerWrapper:
    """Docker命令包装器"""
    def __init__(self):
        self.use_sudo = False
        try:
            subprocess.run(['docker', 'ps'], 
                         check=True, 
                         capture_output=True)
        except subprocess.CalledProcessError:
            self.use_sudo = True
    
    def run(self, *args, **kwargs):
        cmd = ['run', '-d']
        
        # 添加环境变量
        for k, v in kwargs.get('environment', {}).items():
            cmd.extend(['-e', f'{k}={v}'])
        
        # 添加端口映射
        for container_port, host_port in kwargs.get('ports', {}).items():
            cmd.extend(['-p', f'{host_port}:{container_port}'])
        
        # 添加资源限制
        if 'cpu_period' in kwargs:
            cmd.extend(['--cpu-period', str(kwargs['cpu_period'])])
        if 'cpu_quota' in kwargs:
            cmd.extend(['--cpu-quota', str(kwargs['cpu_quota'])])
        if 'mem_limit' in kwargs:
            cmd.extend(['--memory', kwargs['mem_limit']])
        
        # 添加容器名称
        if 'name' in kwargs:
            cmd.extend(['--name', kwargs['name']])
        
        # 添加镜像名称
        cmd.append(args[0])
        
        # 运行命令
        run_docker_command(cmd)
        return self.get_container(kwargs['name'])
    
    def get_container(self, name):
        """获取容器信息"""
        class Container:
            def __init__(self, name):
                self.name = name
            
            def exec_run(self, cmd):
                return run_docker_command(['exec', self.name] + cmd)
            
            def stop(self):
                return run_docker_command(['stop', self.name])
            
            def remove(self):
                return run_docker_command(['rm', self.name])
            
            @property
            def status(self):
                try:
                    output = run_docker_command(['inspect', '--format', '{{.State.Status}}', self.name])
                    return output.strip()
                except subprocess.CalledProcessError:
                    return "未找到"
        
        return Container(name)
    
    def images(self):
        class Images:
            def build(self, **kwargs):
                cmd = ['build']
                if 'tag' in kwargs:
                    cmd.extend(['-t', kwargs['tag']])
                if 'dockerfile' in kwargs:
                    cmd.extend(['-f', kwargs['dockerfile']])
                cmd.append(kwargs['path'])
                return run_docker_command(cmd)
            
            def get(self, name):
                try:
                    run_docker_command(['inspect', name])
                    return True
                except subprocess.CalledProcessError:
                    raise docker.errors.ImageNotFound(f"Image {name} not found")
        
        return Images()

# 初始化Docker客户端
client = DockerWrapper()

CONFIG_FILE = 'containers.json'
BASE_IMAGE_NAME = 'dotmachine-base'
AVAILABLE_IMAGES = {
    'php': 'dotmachine-php',
    'python': 'dotmachine-python',
    'base': 'dotmachine-base'
}
BASE_HTTP_PORT = 4000
BASE_SSH_PORT = 4100
BASE_FTP_PORT = 4200

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {'containers': {}, 'next_id': 1}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def build_image(image_type='base'):
    console.print(f"构建{image_type}镜像中...", style="yellow")
    
    # 首先构建基础镜像
    if image_type != 'base':
        client.images.build(
            path=".",
            dockerfile="Dockerfile.base",
            tag=BASE_IMAGE_NAME,
            rm=True
        )
    
    # 构建指定类型的镜像
    dockerfile = f"Dockerfile.{image_type}" if image_type != 'base' else "Dockerfile.base"
    client.images.build(
        path=".",
        dockerfile=dockerfile,
        tag=AVAILABLE_IMAGES[image_type],
        rm=True
    )
    console.print("镜像构建完成！", style="green")

def get_container_name(container_id):
    return f"dotmachine-{container_id}"

def generate_username():
    """生成随机用户名：dotm-6位数字"""
    numbers = ''.join(random.choices(string.digits, k=6))
    return f"dotm-{numbers}"

def generate_password():
    """生成随机密码：12位字母数字组合"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=12))

@click.group()
def cli():
    """DotMachine - 轻量级VPS管理工具"""
    pass

@cli.command()
@click.argument('username', required=False)
@click.argument('password', required=False)
@click.option('--type', '-t', type=click.Choice(['base', 'php', 'python']), default='base', help='容器类型')
@click.option('--cpu', default=0.03, help='CPU核心数 (默认0.03，即30mCPU)')
@click.option('--memory', default=51.2, help='内存限制(MB)')
def create(username, password, type, cpu, memory):
    """创建新的容器实例。如果不提供用户名和密码，将自动生成。"""
    if username is None:
        username = generate_username()
    if password is None:
        password = generate_password()

    config = load_config()
    container_id = config['next_id']
    container_name = get_container_name(container_id)

    # 确保镜像存在
    image_name = AVAILABLE_IMAGES[type]
    try:
        client.images.get(image_name)
    except docker.errors.ImageNotFound:
        build_image(type)

    # 创建并启动容器
    ports = {
        '22/tcp': BASE_SSH_PORT + container_id,
        '21/tcp': BASE_FTP_PORT + container_id,
        '80/tcp': BASE_HTTP_PORT + container_id
    }

    # 创建数据目录
    data_dir = f"./data/containers/{container_id}"
    os.makedirs(data_dir, exist_ok=True)
    
    container = client.containers.run(
        image_name,
        name=container_name,
        detach=True,
        ports=ports,
        cpu_period=100000,
        cpu_quota=int(cpu * 100000),  # 转换CPU核心数为配额
        mem_limit=f'{memory}m',
        volumes={
            os.path.abspath(data_dir): {
                'bind': '/data',
                'mode': 'rw'
            }
        },
        environment={
            'CONTAINER_USER': username,
            'CONTAINER_PASSWORD': password
        }
    )

    # 在容器中创建用户
    container.exec_run(['/usr/local/bin/create_user.sh', username, password])

    # 更新配置
    config['containers'][container_id] = {
        'name': container_name,
        'username': username,
        'http_port': BASE_HTTP_PORT + container_id,
        'ssh_port': BASE_SSH_PORT + container_id,
        'ftp_port': BASE_FTP_PORT + container_id
    }
    config['next_id'] = container_id + 1
    save_config(config)

    console.print("容器创建成功！", style="green")
    console.print(f"用户名: {username}")
    console.print(f"密码: {password}")
    console.print(f"SSH端口: {BASE_SSH_PORT + container_id}")
    console.print(f"FTP端口: {BASE_FTP_PORT + container_id}")
    if type == 'php':
        console.print(f"PHP-FPM端口: {BASE_HTTP_PORT + container_id}")

@cli.command()
@click.argument('container_id', type=int)
def remove(container_id):
    """删除指定的容器实例"""
    config = load_config()
    if str(container_id) not in config['containers']:
        console.print(f"错误：容器 {container_id} 不存在", style="red")
        return

    container_name = get_container_name(container_id)
    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()
        del config['containers'][str(container_id)]
        save_config(config)
        console.print(f"容器 {container_id} 已成功删除", style="green")
    except docker.errors.NotFound:
        console.print(f"错误：找不到容器 {container_id}", style="red")

@cli.command()
def list():
    """列出所有容器实例"""
    config = load_config()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("名称")
    table.add_column("用户名")
    table.add_column("HTTP端口")
    table.add_column("SSH端口")
    table.add_column("FTP端口")
    table.add_column("状态")

    for container_id, info in config['containers'].items():
        try:
            container = client.containers.get(info['name'])
            status = container.status
        except docker.errors.NotFound:
            status = "未找到"

        table.add_row(
            container_id,
            info['name'],
            info['username'],
            str(info['http_port']),
            str(info['ssh_port']),
            str(info['ftp_port']),
            status
        )

    console.print(table)

if __name__ == '__main__':
    cli()
