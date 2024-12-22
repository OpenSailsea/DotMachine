FROM ubuntu:22.04

# 避免交互式提示
ENV DEBIAN_FRONTEND=noninteractive

# 安装基本工具和PHP 8.2
RUN apt-get update && apt-get install -y \
    software-properties-common \
    && add-apt-repository ppa:ondrej/php \
    && apt-get update \
    && apt-get install -y \
    php8.2-fpm \
    php8.2-cli \
    php8.2-common \
    php8.2-mysql \
    php8.2-zip \
    php8.2-gd \
    php8.2-mbstring \
    php8.2-curl \
    php8.2-xml \
    php8.2-bcmath \
    openssh-server \
    vsftpd \
    sudo \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 配置SSH
RUN mkdir /var/run/sshd
RUN echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config

# 配置vsftpd
RUN echo "listen=YES" > /etc/vsftpd.conf \
    && echo "local_enable=YES" >> /etc/vsftpd.conf \
    && echo "write_enable=YES" >> /etc/vsftpd.conf \
    && echo "chroot_local_user=YES" >> /etc/vsftpd.conf \
    && echo "allow_writeable_chroot=YES" >> /etc/vsftpd.conf \
    && echo "pasv_enable=YES" >> /etc/vsftpd.conf \
    && echo "pasv_min_port=30000" >> /etc/vsftpd.conf \
    && echo "pasv_max_port=31000" >> /etc/vsftpd.conf

# 创建用户脚本
COPY create_user.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/create_user.sh

# 启动脚本
COPY start.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 22 21 9000

CMD ["/usr/local/bin/start.sh"]
