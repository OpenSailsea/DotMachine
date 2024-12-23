from flask import Blueprint, request, redirect, url_for, render_template, session, jsonify
from flask_socketio import emit
from auth import login_required
from extensions import socketio
import threading
import time
import subprocess
from models import DockerManager
from utils import (
    validate_user_container,
    get_container_name,
    generate_password,
    load_config,
    save_config
)

system = Blueprint('system', __name__, url_prefix='/system')
docker_manager = DockerManager()

# 存储状态更新线程
status_threads = {}

@system.route('/dashboard')
@login_required
def dashboard():
    """系统管理面板"""
    try:
        container_id = request.args.get('container_id')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        return render_template('system/dashboard.html',
                             container_id=container_id,
                             user=session['user'],
                             user_container=True)
    except Exception as e:
        return f"加载系统管理面板失败: {str(e)}", 500

@system.route('/status')
@login_required
def get_status():
    """获取容器状态"""
    try:
        container_id = request.args.get('container_id')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return jsonify({'error': '无权操作此容器'}), 403
            
        container_name = get_container_name(int(container_id))
        status = docker_manager.get_container_status(container_name)
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def send_status_updates(container_id: str, user_id: str):
    """定时发送状态更新"""
    while True:
        try:
            # 验证容器所有权
            config = load_config()
            if not validate_user_container(config, container_id, user_id):
                break
                
            container_name = get_container_name(int(container_id))
            status = docker_manager.get_container_status(container_name)
            
            # 发送状态更新
            socketio.emit(f'status_update_{container_id}', status, room=user_id)
            
            # 每3秒更新一次
            time.sleep(3)
        except Exception as e:
            print(f"状态更新错误: {str(e)}")
            break

@socketio.on('connect')
def handle_connect():
    """处理websocket连接"""
    if 'user' not in session:
        return False
    return True

@socketio.on('join')
def handle_join(data):
    """处理加入房间"""
    if 'user' not in session:
        return
        
    container_id = data.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器所有权
    config = load_config()
    if not validate_user_container(config, container_id, user_id):
        return
        
    # 加入用户专属房间
    emit('join', {'status': 'success'})
    
    # 停止已存在的状态更新线程
    thread_key = f"{container_id}_{user_id}"
    if thread_key in status_threads:
        status_threads[thread_key] = False
    
    # 启动新的状态更新线程
    status_thread = threading.Thread(
        target=send_status_updates,
        args=(container_id, user_id)
    )
    status_thread.daemon = True
    status_threads[thread_key] = True
    status_thread.start()

@socketio.on('disconnect')
def handle_disconnect():
    """处理断开连接"""
    if 'user' not in session:
        return
        
    user_id = str(session['user']['id'])
    
    # 停止所有该用户的状态更新线程
    for thread_key in list(status_threads.keys()):
        if thread_key.endswith(user_id):
            status_threads[thread_key] = False

@system.route('/reset_password', methods=['POST'])
@login_required
def reset_password():
    """重置密码"""
    try:
        container_id = request.form.get('container_id')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        container_info = config['containers'][container_id]
        
        # 生成新密码
        new_password = generate_password()
        
        # 更新容器中的用户密码
        container_name = get_container_name(int(container_id))
        container = docker_manager.get_container(container_name)
        if not container:
            return "容器不存在", 404
            
        try:
            subprocess.run(['sudo', 'docker', 'exec', container_name, '/usr/local/bin/create_user.sh', container_info['username'], new_password], check=True)
        except subprocess.CalledProcessError as e:
            return f"重置密码失败: {e.stderr.decode() if e.stderr else str(e)}", 500
        
        # 更新配置中的密码
        config['containers'][container_id]['password'] = new_password
        save_config(config)
        
        return render_template('system/password_reset.html',
                             username=container_info['username'],
                             password=new_password,
                             user=session['user'],
                             user_container=True)
    except Exception as e:
        return f"重置密码失败: {str(e)}", 500

@system.route('/reset', methods=['POST'])
@login_required
def reset_system():
    """重置系统"""
    try:
        container_id = request.form.get('container_id')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        container_info = config['containers'][container_id]
        container_name = get_container_name(int(container_id))
        
        # 停止并删除旧容器
        old_container = docker_manager.get_container(container_name)
        if old_container:
            try:
                subprocess.run(['sudo', 'docker', 'stop', container_name], check=True)
                subprocess.run(['sudo', 'docker', 'rm', container_name], check=True)
            except subprocess.CalledProcessError as e:
                return f"停止并删除旧容器失败: {e.stderr.decode() if e.stderr else str(e)}", 500
        
        # 生成新密码
        new_password = generate_password()
        
        # 创建新容器
        container_type = container_info.get('type', 'base')
        image_name = f'dotmachine-{container_type}'
        
        # 创建数据目录
        from utils import ensure_data_dir
        data_dir = ensure_data_dir(int(container_id))
        
        # 创建新容器
        container = docker_manager.create_container(
            container_id=int(container_id),
            username=container_info['username'],
            password=new_password,
            container_type=container_type
        )
        
        # 更新配置中的密码
        config['containers'][container_id]['password'] = new_password
        save_config(config)
        
        return render_template('system/system_reset.html',
                             username=container_info['username'],
                             password=new_password,
                             user=session['user'],
                             user_container=True)
    except Exception as e:
        return f"重置系统失败: {str(e)}", 500

@system.route('/power/<action>', methods=['POST'])
@login_required
def power_action(action):
    """电源管理"""
    try:
        container_id = request.form.get('container_id')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        # 获取容器
        container_name = get_container_name(int(container_id))
        container = docker_manager.get_container(container_name)
        if not container:
            return "容器不存在", 404
            
        # 执行操作
        try:
            if action == 'start':
                subprocess.run(['sudo', 'docker', 'start', container_name], check=True)
            elif action == 'stop':
                subprocess.run(['sudo', 'docker', 'stop', container_name], check=True)
            elif action == 'restart':
                subprocess.run(['sudo', 'docker', 'restart', container_name], check=True)
            else:
                return "无效的操作", 400
        except subprocess.CalledProcessError as e:
            return f"操作失败: {e.stderr.decode() if e.stderr else str(e)}", 500
        
        return redirect(url_for('index.index_view'))
    except Exception as e:
        return f"操作失败: {str(e)}", 500
