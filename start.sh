#!/bin/bash

# 启动SSH服务
/usr/sbin/sshd

# 启动FTP服务
/usr/sbin/vsftpd &

# 如果安装了PHP-FPM，则启动它
if [ -f /usr/sbin/php-fpm8.2 ]; then
    mkdir -p /run/php
    /usr/sbin/php-fpm8.2 --fpm-config /etc/php/8.2/fpm/php-fpm.conf
fi

# 启动nginx
nginx -g 'daemon off;' &

# 保持容器运行
tail -f /dev/null
