#!/bin/bash

# 安装nginx
if ! command -v nginx &> /dev/null; then
    apt-get update
    apt-get install -y nginx
fi

# 创建配置目录
mkdir -p /etc/nginx/vhost.d

# 配置nginx
cp nginx-proxy.conf /etc/nginx/sites-available/default
ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# 重启nginx
systemctl restart nginx

echo "Host setup completed successfully!"
