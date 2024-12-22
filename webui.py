#!/usr/bin/env python3
from flask import Flask, session, redirect, request, render_template_string, url_for
from requests_oauthlib import OAuth2Session
import os
import json
from dotmachine import DockerWrapper, load_config, save_config, get_container_name, run_docker_command
from functools import wraps

# 允许 OAuth2 使用 HTTP (仅用于开发环境)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于会话加密

# OAuth2 配置
CLIENT_ID = "hi3geJYfTotoiR5S62u3rh4W5tSeC5UG"
CLIENT_SECRET = "VMPBVoAfOB5ojkGXRDEtzvDhRLENHpaN"
REDIRECT_URI = "http://localhost:8181/oauth2/callback"
AUTH_BASE_URL = "https://connect.linux.do/oauth2/authorize"
TOKEN_URL = "https://connect.linux.do/oauth2/token"
USER_INFO_URL = "https://connect.linux.do/api/user"

# Docker 客户端
client = DockerWrapper()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        if session['user'].get('trust_level', 0) < 2:
            return render_template_string("""
                <h1>权限不足</h1>
                <p>需要信任等级 2 以上的用户才能访问此功能。</p>
                <p>您当前的信任等级: {{ trust_level }}</p>
                <p><a href="/logout">退出登录</a></p>
            """, trust_level=session['user'].get('trust_level', 0))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    config = load_config()
    user_id = str(session['user']['id'])
    
    # 查找用户的容器
    user_container = None
    container_id = None
    for cid, info in config['containers'].items():
        if info.get('user_id') == user_id:
            user_container = info
            container_id = cid
            break
            
    # 获取最大机器数量设置（默认95）
    max_machines = config.get('max_machines', 95)
    
    # 计算当前机器数量和百分比
    total_machines = len(config['containers'])
    machine_percentage = (total_machines / max_machines) * 100
    
    # 计算容器剩余天数
    expires_days = 0
    if user_container and 'expires_at' in user_container:
        from datetime import datetime
        # 移除Z后缀和可能存在的微秒部分
        expires_at_str = user_container['expires_at'].rstrip('Z').split('.')[0]
        expires_at = datetime.strptime(expires_at_str, '%Y-%m-%dT%H:%M:%S')
        now = datetime.utcnow()
        expires_days = (expires_at - now).days
    
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DotMachine Web UI</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .info-box { background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 20px 0; }
                .button { 
                    display: inline-block; 
                    padding: 10px 20px; 
                    background: #007bff; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px;
                    margin: 10px 0;
                }
                .button.delete { background: #dc3545; }
                .user-info { margin-bottom: 20px; }
                .progress-container {
                    width: 100%;
                    background-color: #f0f0f0;
                    border-radius: 5px;
                    margin: 20px 0;
                    padding: 3px;
                }
                .progress-bar {
                    height: 20px;
                    background-color: {{ 'red' if machine_percentage >= 100 else '#4CAF50' }};
                    border-radius: 3px;
                    width: {{ machine_percentage }}%;
                    transition: width 0.5s ease-in-out;
                }
                .progress-text {
                    text-align: center;
                    margin-top: 5px;
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="progress-container">
                    <div class="progress-bar"></div>
                </div>
                <div class="progress-text">
                    当前系统机器数量: {{ total_machines }}/{{ max_machines }} ({{ "%.1f"|format(machine_percentage) }}%)
                </div>
                <div class="user-info">
                    <h2>用户信息</h2>
                    <p>用户名: {{ user.username }}</p>
                    <p>信任等级: {{ user.trust_level }}</p>
                    <a href="/logout" class="button">退出登录</a>
                </div>
                
                {% if user_container %}
                    <div class="info-box">
                        <h2>您的 VPS 信息</h2>
                        <p>容器名称: {{ user_container.name }}</p>
                        <p>SSH 用户名: {{ user_container.username }}</p>
                        <p>SSH 端口: {{ user_container.ssh_port }}</p>
                        <p>FTP 端口: {{ user_container.ftp_port }}</p>
                        <p>HTTP 端口: {{ user_container.http_port }}</p>
                        
                        {% if user_container.expires_at %}
                        <div style="margin: 20px 0; padding: 15px; background-color: {% if (expires_days <= 1) %}#ffebee{% elif (expires_days <= 5) %}#fff3e0{% else %}#e8f5e9{% endif %}; border-radius: 5px; border: 1px solid #ddd;">
                            <h3 style="margin-top: 0;">VPS 有效期</h3>
                            <p>创建时间: {{ user_container.created_at[:10] }}</p>
                            <p>到期时间: {{ user_container.expires_at[:10] }}</p>
                            <p>剩余天数: {{ expires_days }} 天</p>
                            {% if expires_days <= 5 %}
                            <form action="/renew" method="post" style="display: inline-block;">
                                <input type="hidden" name="container_id" value="{{ container_id }}">
                                <button type="submit" class="button" style="background: #4CAF50;">续期 5 天</button>
                            </form>
                            {% endif %}
                        </div>
                        {% endif %}
                        
                        <h3>网站管理</h3>
                        <div class="website-list">
                            {% if user_container.get('websites', []) %}
                                <table style="width: 100%; margin-bottom: 20px;">
                                    <tr>
                                        <th>域名</th>
                                        <th>操作</th>
                                    </tr>
                                    {% for website in user_container.get('websites', []) %}
                                    <tr>
                                        <td>{{ website }}</td>
                                        <td>
                                            <form action="/remove_website" method="post" style="display: inline;">
                                                <input type="hidden" name="container_id" value="{{ container_id }}">
                                                <input type="hidden" name="domain" value="{{ website }}">
                                                <button type="submit" class="button delete" 
                                                        onclick="return confirm('确定要删除此网站吗？')">删除</button>
                                            </form>
                                        </td>
                                    </tr>
                                    {% endfor %}
                                </table>
                            {% else %}
                                <p>暂无网站</p>
                            {% endif %}
                            
            <form action="/add_website" method="post">
                <input type="hidden" name="container_id" value="{{ container_id }}">
                <input type="text" name="domain" placeholder="输入域名" required 
                       pattern="^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$"
                       title="请输入有效的域名，如example.com或sub.example.com">
                <button type="submit" class="button">添加网站</button>
            </form>
            <p style="margin-top: 10px; color: #666;">
                提示：添加网站后，请将域名解析到服务器IP，解析生效后即可通过域名访问。
            </p>
                        </div>
                        
                        <div style="margin-top: 20px;">
                            <div style="margin-bottom: 10px;">
                                <form action="/power/stop" method="post" style="display: inline-block; margin-right: 10px;">
                                    <input type="hidden" name="container_id" value="{{ container_id }}">
                                    <button type="submit" class="button" style="background: #dc3545;">关机</button>
                                </form>
                                <form action="/power/start" method="post" style="display: inline-block; margin-right: 10px;">
                                    <input type="hidden" name="container_id" value="{{ container_id }}">
                                    <button type="submit" class="button" style="background: #28a745;">开机</button>
                                </form>
                                <form action="/power/restart" method="post" style="display: inline-block;">
                                    <input type="hidden" name="container_id" value="{{ container_id }}">
                                    <button type="submit" class="button" style="background: #ffc107; color: black;">重启</button>
                                </form>
                            </div>
                            <div>
                                <form action="/reset_password" method="post" style="display: inline-block; margin-right: 10px;">
                                    <input type="hidden" name="container_id" value="{{ container_id }}">
                                    <button type="submit" class="button" style="background: #28a745;">重置密码</button>
                                </form>
                                <form action="/reset_system" method="post" style="display: inline-block; margin-right: 10px;">
                                    <input type="hidden" name="container_id" value="{{ container_id }}">
                                    <button type="submit" class="button" style="background: #ffc107; color: black;" 
                                            onclick="return confirm('确定要重置系统吗？这将清除所有数据！')">重置系统</button>
                                </form>
                                <form action="/remove" method="post" style="display: inline-block;">
                                    <input type="hidden" name="container_id" value="{{ container_id }}">
                                    <button type="submit" class="button delete" 
                                            onclick="return confirm('确定要删除此 VPS 吗？')">删除 VPS</button>
                                </form>
                            </div>
                        </div>
                    </div>
                {% else %}
                    <div class="info-box">
                        <h2>创建 VPS</h2>
                        <p>您还没有创建 VPS</p>
                        <form action="/create" method="post">
                            <select name="type">
                                <option value="base">基础版</option>
                                <option value="php">PHP 版</option>
                                <option value="python">Python 版</option>
                            </select>
                            <button type="submit" class="button">创建 VPS</button>
                        </form>
                    </div>
                {% endif %}
            </div>
        </body>
        </html>
    """, user=session['user'], 
        user_container=user_container, 
        container_id=container_id,
        total_machines=total_machines,
        machine_percentage=machine_percentage,
        expires_days=expires_days)

@app.route('/login')
def login():
    oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI)
    authorization_url, state = oauth.authorization_url(AUTH_BASE_URL)
    session['oauth_state'] = state
    return redirect(authorization_url)

@app.route('/oauth2/callback')
def callback():
    oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=session.get('oauth_state'))
    token = oauth.fetch_token(
        TOKEN_URL,
        client_secret=CLIENT_SECRET,
        authorization_response=request.url
    )
    
    # 获取用户信息
    user_info = oauth.get(USER_INFO_URL).json()
    session['user'] = user_info
    session['oauth_token'] = token
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/create', methods=['POST'])
@login_required
def create():
    config = load_config()
    user_id = str(session['user']['id'])
    
    # 检查用户是否已有容器
    for info in config['containers'].values():
        if info.get('user_id') == user_id:
            return "您已经创建了一个 VPS", 400
            
    # 获取最大机器数量设置（默认95）
    max_machines = config.get('max_machines', 95)
    
    # 检查总机器数量是否超过限制
    if len(config['containers']) >= max_machines:
        return "当前系统机器数量已达到上限，暂时无法创建新的 VPS", 400
    
    # 创建新容器
    container_id = config['next_id']
    container_name = get_container_name(container_id)
    
    # 生成随机用户名和密码
    import random
    import string
    username = f"dotm-{session['user']['username']}"
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    # 设置端口
    from dotmachine import BASE_HTTP_PORT, BASE_SSH_PORT, BASE_FTP_PORT
    
    # 创建容器
    container_type = request.form.get('type', 'base')
    image_name = f'dotmachine-{container_type}'
    
    # 确保镜像存在
    try:
        import subprocess
        # 检查镜像是否存在
        subprocess.run(['sudo', 'docker', 'inspect', image_name], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # 如果镜像不存在，构建它
        subprocess.run(['sudo', 'docker', 'build', '-t', image_name, '-f', f'Dockerfile.{container_type}', '.'], check=True)
    
    # 创建数据目录
    data_dir = f"./data/containers/{container_id}"
    os.makedirs(data_dir, exist_ok=True)
    
    # 创建容器
    container = client.run(
        image_name,
        name=container_name,
        ports={
            '22': f"{BASE_SSH_PORT + container_id}",
            '21': f"{BASE_FTP_PORT + container_id}",
            '9000': f"{BASE_HTTP_PORT + container_id}"
        },
        volumes={
            os.path.abspath(data_dir): {
                'bind': '/data',
                'mode': 'rw'
            }
        },
        cpu_period=100000,
            cpu_quota=3000,  # 0.03 CPU (30mCPU)
            mem_limit='51.2m',
            storage_opt={'size': '3G'},  # 3GB硬盘空间限制
        environment={
            'CONTAINER_USER': username,
            'CONTAINER_PASSWORD': password
        }
    )
    
    # 在容器中创建用户
    container.exec_run(['/usr/local/bin/create_user.sh', username, password])
    
    # 更新配置
    config['containers'][str(container_id)] = {
        'name': container_name,
        'username': username,
        'user_id': user_id,
        'http_port': BASE_HTTP_PORT + container_id,
        'ssh_port': BASE_SSH_PORT + container_id,
        'ftp_port': BASE_FTP_PORT + container_id
    }
    config['next_id'] = container_id + 1
    # 保存密码、初始化网站列表和有效期
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    config['containers'][str(container_id)]['password'] = password
    config['containers'][str(container_id)]['websites'] = []
    config['containers'][str(container_id)]['created_at'] = now.isoformat() + 'Z'
    config['containers'][str(container_id)]['expires_at'] = (now + timedelta(days=5)).isoformat() + 'Z'
    save_config(config)
    
    return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>VPS 创建成功</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .container { max-width: 800px; margin: 0 auto; }
                .info-box { 
                    background: #f5f5f5; 
                    padding: 20px; 
                    border-radius: 5px; 
                    margin: 20px 0;
                    border: 1px solid #ddd;
                }
                .warning {
                    color: red;
                    font-weight: bold;
                }
                .button { 
                    display: inline-block; 
                    padding: 10px 20px; 
                    background: #007bff; 
                    color: white; 
                    text-decoration: none; 
                    border-radius: 5px;
                    margin: 10px 0;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>VPS 创建成功！</h1>
                <div class="info-box">
                    <h2>登录信息</h2>
                    <p>SSH/FTP 用户名: {{ username }}</p>
                    <p>SSH/FTP 密码: {{ password }}</p>
                    <p class="warning">请立即保存这些信息！这是显示密码的唯一机会。</p>
                    <p>SSH 端口: {{ ssh_port }}</p>
                    <p>FTP 端口: {{ ftp_port }}</p>
                    <p>HTTP 端口: {{ http_port }}</p>
                </div>
                <a href="/" class="button">返回主页</a>
            </div>
        </body>
        </html>
    """, username=username, password=password,
        ssh_port=BASE_SSH_PORT + container_id,
        ftp_port=BASE_FTP_PORT + container_id,
        http_port=BASE_HTTP_PORT + container_id)

@app.route('/remove', methods=['POST'])
@login_required
def remove():
    config = load_config()
    container_id = request.form.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器属于当前用户
    container_info = config['containers'].get(container_id)
    if not container_info or container_info.get('user_id') != user_id:
        return "无权操作此容器", 403
    
    # 停止并删除容器
    container_name = get_container_name(int(container_id))
    try:
        container = client.get_container(container_name)
        container.stop()
        container.remove()
        
        # 导入端口常量
        from dotmachine import BASE_HTTP_PORT, BASE_SSH_PORT, BASE_FTP_PORT
        
        # 删除当前容器
        del config['containers'][container_id]
        
        # 重新整理 ID，将大于当前 ID 的容器 ID 减 1
        new_containers = {}
        current_id = int(container_id)
        for cid, info in config['containers'].items():
            cid = int(cid)
            if cid < current_id:
                new_containers[str(cid)] = info
            else:
                # 更新容器名称和端口
                new_id = cid - 1
                new_name = get_container_name(new_id)
                old_name = info['name']
                
                # 重命名容器和移动数据目录
                try:
                    # 停止并删除旧容器
                    container = client.get_container(old_name)
                    container.stop()
                    container.remove()
                    
                    # 移动数据目录
                    old_data_dir = f"./data/containers/{cid}"
                    new_data_dir = f"./data/containers/{new_id}"
                    if os.path.exists(old_data_dir):
                        if os.path.exists(new_data_dir):
                            import shutil
                            shutil.rmtree(new_data_dir)
                        os.rename(old_data_dir, new_data_dir)
                    
                    # 创建新容器
                    container = client.run(
                        f'dotmachine-{info.get("type", "base")}',
                        name=new_name,
                        ports={
                            '22': f"{BASE_SSH_PORT + new_id}",
                            '21': f"{BASE_FTP_PORT + new_id}",
                            '9000': f"{BASE_HTTP_PORT + new_id}"
                        },
                        volumes={
                            os.path.abspath(new_data_dir): {
                                'bind': '/data',
                                'mode': 'rw'
                            }
                        },
                        cpu_period=100000,
                        cpu_quota=3000,  # 0.03 CPU (30mCPU)
                        mem_limit='51.2m',
                        storage_opt={'size': '3G'},  # 3GB硬盘空间限制
                        environment={
                            'CONTAINER_USER': info['username'],
                            'CONTAINER_PASSWORD': info['password']
                        }
                    )
                    
                    # 在容器中创建用户
                    container.exec_run(['/usr/local/bin/create_user.sh', info['username'], info['password']])
                except:
                    pass
                
                # 更新配置
                info['name'] = new_name
                info['http_port'] = BASE_HTTP_PORT + new_id
                info['ssh_port'] = BASE_SSH_PORT + new_id
                info['ftp_port'] = BASE_FTP_PORT + new_id
                new_containers[str(new_id)] = info
        
        # 更新配置
        config['containers'] = new_containers
        config['next_id'] = max([int(i) for i in new_containers.keys()], default=0) + 1
        save_config(config)
    except Exception as e:
        return f"删除容器失败: {str(e)}", 500
    
    return redirect(url_for('index'))

@app.route('/reset_password', methods=['POST'])
@login_required
def reset_password():
    config = load_config()
    container_id = request.form.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器属于当前用户
    container_info = config['containers'].get(container_id)
    if not container_info or container_info.get('user_id') != user_id:
        return "无权操作此容器", 403
    
    # 生成新密码
    import random
    import string
    new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    
    # 更新容器中的用户密码
    container_name = get_container_name(int(container_id))
    try:
        container = client.get_container(container_name)
        container.exec_run(['/usr/local/bin/create_user.sh', container_info['username'], new_password])
        
        # 更新配置中的密码
        config['containers'][container_id]['password'] = new_password
        save_config(config)
        
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>密码重置成功</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .info-box { 
                        background: #f5f5f5; 
                        padding: 20px; 
                        border-radius: 5px; 
                        margin: 20px 0;
                        border: 1px solid #ddd;
                    }
                    .warning {
                        color: red;
                        font-weight: bold;
                    }
                    .button { 
                        display: inline-block; 
                        padding: 10px 20px; 
                        background: #007bff; 
                        color: white; 
                        text-decoration: none; 
                        border-radius: 5px;
                        margin: 10px 0;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>密码重置成功！</h1>
                    <div class="info-box">
                        <h2>新的登录信息</h2>
                        <p>SSH/FTP 用户名: {{ username }}</p>
                        <p>SSH/FTP 新密码: {{ password }}</p>
                        <p class="warning">请立即保存新密码！这是显示密码的唯一机会。</p>
                    </div>
                    <a href="/" class="button">返回主页</a>
                </div>
            </body>
            </html>
        """, username=container_info['username'], password=new_password)
    except Exception as e:
        return f"重置密码失败: {str(e)}", 500

@app.route('/power/start', methods=['POST'])
@login_required
def power_start():
    config = load_config()
    container_id = request.form.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器属于当前用户
    container_info = config['containers'].get(container_id)
    if not container_info or container_info.get('user_id') != user_id:
        return "无权操作此容器", 403
    
    try:
        # 启动容器
        container_name = get_container_name(int(container_id))
        run_docker_command(['start', container_name])
        return redirect(url_for('index'))
    except Exception as e:
        return f"启动失败: {str(e)}", 500

@app.route('/power/stop', methods=['POST'])
@login_required
def power_stop():
    config = load_config()
    container_id = request.form.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器属于当前用户
    container_info = config['containers'].get(container_id)
    if not container_info or container_info.get('user_id') != user_id:
        return "无权操作此容器", 403
    
    try:
        # 停止容器
        container_name = get_container_name(int(container_id))
        run_docker_command(['stop', container_name])
        return redirect(url_for('index'))
    except Exception as e:
        return f"关机失败: {str(e)}", 500

@app.route('/power/restart', methods=['POST'])
@login_required
def power_restart():
    config = load_config()
    container_id = request.form.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器属于当前用户
    container_info = config['containers'].get(container_id)
    if not container_info or container_info.get('user_id') != user_id:
        return "无权操作此容器", 403
    
    try:
        # 重启容器
        container_name = get_container_name(int(container_id))
        run_docker_command(['restart', container_name])
        return redirect(url_for('index'))
    except Exception as e:
        return f"重启失败: {str(e)}", 500

@app.route('/reset_system', methods=['POST'])
@login_required
def reset_system():
    config = load_config()
    container_id = request.form.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器属于当前用户
    container_info = config['containers'].get(container_id)
    if not container_info or container_info.get('user_id') != user_id:
        return "无权操作此容器", 403
    
    container_name = get_container_name(int(container_id))
    try:
        # 停止并删除旧容器
        old_container = client.get_container(container_name)
        old_container.stop()
        old_container.remove()
        
        # 生成新密码
        import random
        import string
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        
        # 创建新容器
        container_type = request.form.get('type', 'base')
        image_name = f'dotmachine-{container_type}'
        
        # 创建数据目录（如果不存在）
        data_dir = f"./data/containers/{container_id}"
        os.makedirs(data_dir, exist_ok=True)
        
        # 创建新容器
        container = client.run(
            image_name,
            name=container_name,
            ports={
                '22': f"{container_info['ssh_port']}",
                '21': f"{container_info['ftp_port']}",
                '9000': f"{container_info['http_port']}"
            },
            volumes={
                os.path.abspath(data_dir): {
                    'bind': '/data',
                    'mode': 'rw'
                }
            },
            cpu_period=100000,
            cpu_quota=3000,  # 0.03 CPU (30mCPU)
            mem_limit='51.2m',
            storage_opt={'size': '3G'},  # 3GB硬盘空间限制
            environment={
                'CONTAINER_USER': container_info['username'],
                'CONTAINER_PASSWORD': new_password
            }
        )
        
        # 在容器中创建用户
        container.exec_run(['/usr/local/bin/create_user.sh', container_info['username'], new_password])
        
        # 更新配置中的密码
        config['containers'][container_id]['password'] = new_password
        save_config(config)
        
        return render_template_string("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>系统重置成功</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; }
                    .container { max-width: 800px; margin: 0 auto; }
                    .info-box { 
                        background: #f5f5f5; 
                        padding: 20px; 
                        border-radius: 5px; 
                        margin: 20px 0;
                        border: 1px solid #ddd;
                    }
                    .warning {
                        color: red;
                        font-weight: bold;
                    }
                    .button { 
                        display: inline-block; 
                        padding: 10px 20px; 
                        background: #007bff; 
                        color: white; 
                        text-decoration: none; 
                        border-radius: 5px;
                        margin: 10px 0;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>系统重置成功！</h1>
                    <div class="info-box">
                        <h2>新的登录信息</h2>
                        <p>SSH/FTP 用户名: {{ username }}</p>
                        <p>SSH/FTP 新密码: {{ password }}</p>
                        <p class="warning">请立即保存新密码！这是显示密码的唯一机会。</p>
                        <p>所有数据已被清除，系统已恢复到初始状态。</p>
                    </div>
                    <a href="/" class="button">返回主页</a>
                </div>
            </body>
            </html>
        """, username=container_info['username'], password=new_password)
    except Exception as e:
        return f"重置系统失败: {str(e)}", 500

@app.route('/add_website', methods=['POST'])
@login_required
def add_website():
    config = load_config()
    container_id = request.form.get('container_id')
    domain = request.form.get('domain')
    user_id = str(session['user']['id'])
    
    # 验证容器属于当前用户
    container_info = config['containers'].get(container_id)
    if not container_info or container_info.get('user_id') != user_id:
        return "无权操作此容器", 403
    
    # 验证域名格式
    import re
    if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}$', domain):
        return "无效的域名格式", 400
    
    try:
        # 获取容器
        container_name = get_container_name(int(container_id))
        container = client.get_container(container_name)
        
        # 在容器中创建网站配置
        container.exec_run(['/usr/local/bin/generate_nginx_config.sh', domain])
        
        # 更新配置
        if 'websites' not in config['containers'][container_id]:
            config['containers'][container_id]['websites'] = []
        config['containers'][container_id]['websites'].append(domain)
        save_config(config)
        
        return redirect(url_for('index'))
    except Exception as e:
        return f"添加网站失败: {str(e)}", 500

@app.route('/renew', methods=['POST'])
@login_required
def renew():
    config = load_config()
    container_id = request.form.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器属于当前用户
    container_info = config['containers'].get(container_id)
    if not container_info or container_info.get('user_id') != user_id:
        return "无权操作此容器", 403
    
    try:
        # 更新有效期
        from datetime import datetime, timedelta
        # 移除Z后缀和可能存在的微秒部分
        expires_at_str = container_info['expires_at'].rstrip('Z').split('.')[0]
        expires_at = datetime.strptime(expires_at_str, '%Y-%m-%dT%H:%M:%S')
        now = datetime.utcnow()
        
        # 如果已过期，从当前时间开始计算
        if expires_at < now:
            new_expires_at = now + timedelta(days=5)
        else:
            # 如果未过期，从原有期限开始追加
            new_expires_at = expires_at + timedelta(days=5)
            
        config['containers'][container_id]['expires_at'] = new_expires_at.isoformat() + 'Z'
        save_config(config)
        
        return redirect(url_for('index'))
    except Exception as e:
        return f"续期失败: {str(e)}", 500

@app.route('/remove_website', methods=['POST'])
@login_required
def remove_website():
    config = load_config()
    container_id = request.form.get('container_id')
    domain = request.form.get('domain')
    user_id = str(session['user']['id'])
    
    # 验证容器属于当前用户
    container_info = config['containers'].get(container_id)
    if not container_info or container_info.get('user_id') != user_id:
        return "无权操作此容器", 403
    
    try:
        # 获取容器
        container_name = get_container_name(int(container_id))
        container = client.get_container(container_name)
        
        # 删除网站配置和目录
        container.exec_run(['rm', '-f', f'/etc/nginx/sites-enabled/{domain}.conf'])
        container.exec_run(['rm', '-rf', f'/data/www/{domain}'])
        container.exec_run(['nginx', '-s', 'reload'])
        
        # 更新配置
        if 'websites' in config['containers'][container_id]:
            config['containers'][container_id]['websites'].remove(domain)
        save_config(config)
        
        return redirect(url_for('index'))
    except Exception as e:
        return f"删除网站失败: {str(e)}", 500

if __name__ == '__main__':
    # 在生产环境中应该使用更安全的密钥
    app.run(host='0.0.0.0', port=8181, debug=True)
