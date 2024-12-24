#!/bin/bash

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then
    echo "请以root权限运行此脚本"
    echo "Usage: sudo $0 <command>"
    exit 1
fi

# 检查是否提供了命令参数
if [ $# -eq 0 ]; then
    echo "Usage: sudo $0 <command>"
    exit 1
fi

# 获取要执行的命令
command="$*"

# 读取容器配置
config_file="containers.json"
if [ ! -f "$config_file" ]; then
    echo "Error: containers.json not found"
    exit 1
fi

# 遍历所有容器
containers=$(jq -r '.containers | to_entries[] | "\(.key) \(.value.name)"' "$config_file" 2>/dev/null)

if [ -z "$containers" ]; then
    echo "Error: 无法解析容器配置文件或容器列表为空"
    exit 1
fi

while read -r container_id container_name; do
    echo "Processing container $container_name..."
    
    # 检查容器状态
    status=$(docker inspect -f '{{.State.Running}}' "$container_name" 2>/dev/null)
    was_stopped=false
    
    # 如果容器不存在，跳过
    if [ $? -ne 0 ]; then
        echo "Container $container_name does not exist, skipping..."
        continue
    fi
    
    # 如果容器已停止，启动它
    if [ "$status" = "false" ]; then
        echo "Starting container $container_name..."
        docker start "$container_name"
        was_stopped=true
    fi
    
    # 执行命令
    echo "Executing command in $container_name: $command"
    docker exec -u root "$container_name" /bin/bash -c "$command"
    
    # 如果容器之前是停止状态，则重新停止
    if [ "$was_stopped" = true ]; then
        echo "Stopping container $container_name..."
        docker stop "$container_name"
    fi
    
    echo "Finished processing $container_name"
    echo "----------------------------------------"
done <<< "$containers"

echo "All containers processed."
