#!/bin/bash

# 检查参数
if [ "$#" -ne 1 ]; then
    echo "Usage: $0 DOMAIN"
    exit 1
fi

DOMAIN=$1
SITE_ROOT="/data/www/$DOMAIN"

# 创建网站目录并设置权限
mkdir -p "$SITE_ROOT"
chown www-data:www-data "$SITE_ROOT"
chmod 775 "$SITE_ROOT"

# 创建默认首页
if [ ! -f "$SITE_ROOT/index.html" ]; then
    cat > "$SITE_ROOT/index.html" <<EOF
<!DOCTYPE html>
<html>
<head>
    <title>Welcome to $DOMAIN</title>
</head>
<body>
    <h1>Welcome to $DOMAIN!</h1>
    <p>This is the default page. You can replace it with your own content.</p>
</body>
</html>
EOF
fi

# 生成容器内的nginx配置
cat > "/etc/nginx/sites-enabled/$DOMAIN.conf" <<EOF
server {
    listen 80;
    server_name localhost;
    root /data/www/$DOMAIN;
    index index.html index.htm index.php;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.2-fpm.sock;
    }
}
EOF

# 生成主机上的nginx配置
CONTAINER_NAME=\$(hostname)
CONTAINER_PORT=\$(docker port \$CONTAINER_NAME 80 2>/dev/null | cut -d ':' -f 2)

if [ ! -z "\$CONTAINER_PORT" ]; then
    # 在主机上创建nginx配置目录
    mkdir -p /etc/nginx/vhost.d

    # 生成反向代理配置
    cat > "/etc/nginx/vhost.d/$DOMAIN.conf" <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:\$CONTAINER_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # 重新加载主机nginx配置
    systemctl reload nginx || nginx -s reload
fi

# 重新加载nginx配置
nginx -s reload

echo "Website $DOMAIN has been configured successfully!"
