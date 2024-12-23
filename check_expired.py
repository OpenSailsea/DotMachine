#!/usr/bin/env python3
import json
import os
from datetime import datetime
from dotmachine import DockerWrapper, get_container_name

def load_config():
    config_file = 'containers.json'
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {'containers': {}, 'next_id': 1}

def save_config(config):
    with open('containers.json', 'w') as f:
        json.dump(config, f, indent=2)

def check_and_remove_expired():
    config = load_config()
    client = DockerWrapper()
    now = datetime.utcnow()
    
    # 遍历所有容器
    expired_containers = []
    for container_id, info in config['containers'].items():
        if 'expires_at' in info:
            # 移除Z后缀和可能存在的微秒部分
            expires_at_str = info['expires_at'].rstrip('Z').split('.')[0]
            expires_at = datetime.strptime(expires_at_str, '%Y-%m-%dT%H:%M:%S')
            
            # 检查是否过期
            if now > expires_at:
                expired_containers.append(container_id)
    
    # 删除过期的容器
    for container_id in expired_containers:
        try:
            container_name = get_container_name(int(container_id))
            container = client.get_container(container_name)
            
            # 停止并删除容器
            container.stop()
            container.remove()
            
            # 删除数据目录
            data_dir = f"./data/containers/{container_id}"
            if os.path.exists(data_dir):
                import shutil
                shutil.rmtree(data_dir)
            
            # 从配置中删除
            del config['containers'][container_id]
            
            print(f"已删除过期容器: {container_name}")
        except Exception as e:
            print(f"删除容器 {container_name} 时出错: {str(e)}")
    
    # 如果有容器被删除,保存更新后的配置
    if expired_containers:
        save_config(config)
        print(f"共删除 {len(expired_containers)} 个过期容器")

if __name__ == '__main__':
    check_and_remove_expired()
