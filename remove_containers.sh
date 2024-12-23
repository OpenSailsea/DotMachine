#!/bin/bash

# 检查参数
if [ $# -ne 2 ]; then
    echo "用法: $0 <起始ID> <结束ID>"
    exit 1
fi

start_id=$1
end_id=$2

# 验证参数是否为数字
case $start_id in
    ''|*[!0-9]*) 
        echo "错误: 起始ID必须为数字"
        exit 1
        ;;
esac

case $end_id in
    ''|*[!0-9]*) 
        echo "错误: 结束ID必须为数字"
        exit 1
        ;;
esac

# 验证起始ID小于结束ID
if [ $start_id -gt $end_id ]; then
    echo "错误: 起始ID必须小于或等于结束ID"
    exit 1
fi

# 容器配置文件路径
config_file="containers.json"

# 检查配置文件是否存在
if [ ! -f "$config_file" ]; then
    echo "错误: 找不到配置文件 $config_file"
    exit 1
fi

# 测试jq是否可用
if ! jq '.' "$config_file" >/dev/null 2>&1; then
    echo "错误: jq命令执行失败,请确保已正确安装jq"
    echo "Ubuntu/Debian: sudo apt-get install jq"
    echo "CentOS/RHEL: sudo yum install jq"
    exit 1
fi

# 遍历ID区间
for id in $(seq $start_id $end_id); do
    container_name="dotm-$id"
    echo "处理容器 $container_name..."
    
    # 停止并删除容器(忽略错误)
    sudo docker stop $container_name 2>/dev/null || true
    sudo docker rm $container_name 2>/dev/null || true
    
    # 删除容器数据目录
    sudo rm -rf "./data/containers/$id" 2>/dev/null || true
    
    # 从配置文件中删除容器记录
    if [ -f "$config_file" ]; then
        # 检查容器是否存在于配置中
        if jq -e ".containers[\"$id\"]" "$config_file" >/dev/null 2>&1; then
            # 获取容器的端口信息并构建端口数组
            ssh_port=$(jq -r ".containers[\"$id\"].ssh_port" "$config_file")
            ftp_port=$(jq -r ".containers[\"$id\"].ftp_port" "$config_file")
            http_port=$(jq -r ".containers[\"$id\"].http_port" "$config_file")
            
            # 删除容器记录并从used_ports中移除端口
            jq --arg id "$id" \
               --arg ssh "$ssh_port" \
               --arg ftp "$ftp_port" \
               --arg http "$http_port" \
               '
                del(.containers[$id]) |
                .used_ports = (.used_ports - [$ssh | tonumber, $ftp | tonumber, $http | tonumber])
            ' "$config_file" > "$config_file.tmp" && mv "$config_file.tmp" "$config_file"
            
            echo "已从配置文件中删除容器 $id 的记录"
        fi
    fi
done

# 更新next_id
# 找到最大的容器ID并设置next_id为其+1，如果没有容器则设置为1
max_id=$(jq -r '.containers | keys | map(tonumber) | max // 0' "$config_file")
next_id=$((max_id + 1))
if [ $next_id -lt 1 ]; then
    next_id=1
fi

jq --arg next_id "$next_id" '.next_id = ($next_id | tonumber)' "$config_file" > "$config_file.tmp" && mv "$config_file.tmp" "$config_file"

echo "完成!"
echo "已删除ID从 $start_id 到 $end_id 的所有容器"
echo "已更新配置文件: next_id = $next_id"
