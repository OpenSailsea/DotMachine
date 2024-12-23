from flask import Blueprint, render_template, session, request
from flask_socketio import emit, join_room, leave_room
from auth import login_required
from extensions import socketio
from utils import validate_user_container, get_container_name, load_config
from models import DockerManager
import pty
import os
import termios
import struct
import fcntl
import subprocess
import select
import threading

terminal = Blueprint('terminal', __name__, url_prefix='/terminal')
docker_manager = DockerManager()

# 存储终端进程
terminals = {}

@terminal.route('/')
@login_required
def terminal_view():
    """终端页面"""
    try:
        container_id = request.args.get('container_id')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        return render_template('terminal/terminal.html',
                             container_id=container_id,
                             user=session['user'])
    except Exception as e:
        return f"加载终端失败: {str(e)}", 500

def set_winsize(fd, row, col, xpix=0, ypix=0):
    """设置终端窗口大小"""
    winsize = struct.pack('HHHH', row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)

def read_and_forward_terminal_output(fd, pid, container_id, user_id):
    """读取并转发终端输出"""
    max_read_bytes = 1024 * 20
    thread_key = f"{container_id}_{user_id}"
    
    while thread_key in terminals:
        timeout_sec = 0.1
        (data_ready, _, _) = select.select([fd], [], [], timeout_sec)
        if data_ready:
            try:
                output = os.read(fd, max_read_bytes)
                socketio.emit(
                    f'terminal_output_{container_id}',
                    {'output': output.decode()},
                    room=user_id
                )
            except Exception as e:
                print(f"读取终端输出错误: {str(e)}")
                break

@socketio.on('terminal_input')
def handle_terminal_input(data):
    """处理终端输入"""
    if 'user' not in session:
        return
        
    container_id = data.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器所有权
    config = load_config()
    if not validate_user_container(config, container_id, user_id):
        return
        
    thread_key = f"{container_id}_{user_id}"
    if thread_key in terminals:
        fd = terminals[thread_key].get('fd')
        if fd:
            os.write(fd, data['input'].encode())

@socketio.on('terminal_resize')
def handle_terminal_resize(data):
    """处理终端大小调整"""
    if 'user' not in session:
        return
        
    container_id = data.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器所有权
    config = load_config()
    if not validate_user_container(config, container_id, user_id):
        return
        
    thread_key = f"{container_id}_{user_id}"
    if thread_key in terminals:
        fd = terminals[thread_key].get('fd')
        if fd:
            set_winsize(fd, data['rows'], data['cols'])

@socketio.on('terminal_connect')
def handle_terminal_connect(data):
    """处理终端连接"""
    if 'user' not in session:
        return
        
    container_id = data.get('container_id')
    user_id = str(session['user']['id'])
    
    # 验证容器所有权
    config = load_config()
    if not validate_user_container(config, container_id, user_id):
        return
        
    # 获取容器信息
    container_info = config['containers'][container_id]
    container_name = get_container_name(int(container_id))
    
    # 创建伪终端
    parent_fd, child_fd = pty.openpty()
    
    # 在容器中启动shell
    container = docker_manager.get_container(container_name)
    if not container:
        emit('terminal_error', {'error': '容器不存在'})
        return
        
    # 使用docker exec启动shell
    cmd = ['sudo', 'docker', 'exec', '-it', container_name, 'su', '-', container_info['username']]
    p = subprocess.Popen(
        cmd,
        stdin=child_fd,
        stdout=child_fd,
        stderr=child_fd,
        preexec_fn=os.setsid
    )
    
    # 设置终端大小
    set_winsize(parent_fd, data['rows'], data['cols'])
    
    # 存储终端信息
    thread_key = f"{container_id}_{user_id}"
    terminals[thread_key] = {
        'fd': parent_fd,
        'pid': p.pid,
        'container_name': container_name
    }
    
    # 启动输出转发线程
    terminal_thread = threading.Thread(
        target=read_and_forward_terminal_output,
        args=(parent_fd, p.pid, container_id, user_id)
    )
    terminal_thread.daemon = True
    terminal_thread.start()
    
    emit('terminal_connected', {'status': 'success'})

@socketio.on('terminal_disconnect')
def handle_terminal_disconnect(data):
    """处理终端断开连接"""
    if 'user' not in session:
        return
        
    container_id = data.get('container_id')
    user_id = str(session['user']['id'])
    thread_key = f"{container_id}_{user_id}"
    
    if thread_key in terminals:
        # 关闭终端
        try:
            fd = terminals[thread_key].get('fd')
            if fd:
                os.close(fd)
        except Exception as e:
            print(f"关闭终端错误: {str(e)}")
            
        # 移除终端信息
        del terminals[thread_key]
