# DotMachine

DotMachine是一个轻量级VPS管理工具，支持多用户、多容器管理，具有Web界面，支持域名绑定和网站托管功能。

## 特性

- 轻量级VPS管理
  - CPU: 30mCPU
  - 内存: 51.2MB
  - 硬盘: 3GB
- Web管理界面
  - 容器状态监控
  - 开关机/重启
  - 密码重置
  - 系统重置
- 网站托管
  - 支持多域名绑定
  - PHP支持
  - Python支持
  - 文件管理(FTP/SFTP)
- 数据持久化
  - 网站文件持久化
  - 系统重置保留数据
  - 容器迁移数据同步

## 安装

1. 安装依赖
```bash
# Ubuntu/Debian
apt-get update
apt-get install -y python3 python3-pip docker.io nginx

# CentOS/RHEL
yum install -y python3 python3-pip docker nginx
```

2. 克隆仓库
```bash
git clone https://github.com/IsCycleBai/DotMachine.git
cd DotMachine
```

3. 安装Python依赖
```bash
pip3 install -r requirements.txt
```

4. 配置主机环境
```bash
sudo chmod +x setup-host.sh
sudo ./setup-host.sh
```

5. 配置OAuth认证
```bash
# 编辑webui.py，修改OAuth配置
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"
REDIRECT_URI = "http://your_domain/oauth2/callback"
AUTH_BASE_URL = "https://linux.do/oauth2/authorize"
TOKEN_URL = "https://linux.do/oauth2/token"
USER_INFO_URL = "https://linux.do/api/user"
```

6. 构建基础镜像
```bash
sudo python3 dotmachine.py build base
```

## 环境要求

- Python 3.6+
- Docker
- Nginx
- 公网IP（用于域名解析）
- OAuth2认证服务器

## 配置说明

1. 主机配置
```bash
# nginx-proxy.conf - 主机Nginx配置
server {
    listen 80;
    server_name _;
    include /etc/nginx/vhost.d/*.conf;
}
```

2. 容器配置
```bash
# 容器资源限制
CPU: 30mCPU (0.03核)
内存: 51.2MB
硬盘: 3GB

# 端口映射
SSH: 41xx
FTP: 42xx
HTTP: 40xx
```

3. 网站配置
```nginx
# 自动生成的网站配置
server {
    listen 80;
    server_name your-domain.com;
    root /data/www/your-domain.com;
    index index.html index.php;
    
    location ~ \.php$ {
        fastcgi_pass unix:/run/php/php8.2-fpm.sock;
        include snippets/fastcgi-php.conf;
    }
}
```

## 使用方法

1. 启动Web界面
```bash
python3 webui.py
```

2. 访问管理界面
```
http://localhost:8181
```

3. 创建VPS
- 选择VPS类型（基础版/PHP版/Python版）
- 系统自动分配端口和账号密码
- 通过SSH/FTP访问VPS

4. 添加网站
- 在Web界面添加网站域名
- 将域名解析到服务器IP
- 通过FTP上传网站文件到 /data/www/你的域名/
- 解析生效后即可通过域名访问

## 目录结构

```
/data/
  └── containers/
      └── {container_id}/
          └── www/
              └── {domain}/
                  └── index.html
```

## 端口说明

- SSH: 41xx (xx为容器ID，如4101)
- FTP: 42xx
- HTTP: 40xx

## 注意事项

1. 域名解析
- 添加网站后需要将域名解析到服务器IP
- 支持多级域名(如blog.example.com)
- 解析生效需要一定时间

2. 数据安全
- 重要数据请及时备份
- 系统重置会保留网站数据
- 删除VPS会永久删除数据

3. 资源限制
- CPU限制为30mCPU
- 内存限制为51.2MB
- 硬盘限制为3GB

## 技术栈

- 后端：Python, Flask
- 容器：Docker
- Web服务器：Nginx
- 数据库：JSON文件存储
- 认证：OAuth2

## 许可证

MIT License
