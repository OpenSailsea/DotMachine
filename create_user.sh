#!/bin/bash

# 检查参数
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 USERNAME PASSWORD"
    exit 1
fi

USERNAME=$1
PASSWORD=$2

# 创建用户
useradd -m -s /bin/bash $USERNAME
echo "$USERNAME:$PASSWORD" | chpasswd

# 将用户添加到www-data组
usermod -a -G www-data $USERNAME

# 确保网站根目录存在并设置权限
mkdir -p /data/www
chown www-data:www-data /data/www
chmod 775 /data/www

# 创建用户的FTP主目录链接
ln -sf /data/www /home/$USERNAME/www
chown -h $USERNAME:$USERNAME /home/$USERNAME/www

# 配置FTP
echo "$USERNAME" >> /etc/vsftpd.userlist
chown -R $USERNAME:$USERNAME /home/$USERNAME

echo "User $USERNAME has been created successfully!"
