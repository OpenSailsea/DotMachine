from flask import Blueprint, request, redirect, url_for, render_template, session
from auth import login_required
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
            
        result = container.exec_run(['/usr/local/bin/create_user.sh', container_info['username'], new_password])
        if result.exit_code != 0:
            return f"重置密码失败: {result.output.decode()}", 500
        
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
            old_container.stop()
            old_container.remove()
        
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
        if action == 'start':
            container.start()
        elif action == 'stop':
            container.stop()
        elif action == 'restart':
            container.restart()
        else:
            return "无效的操作", 400
        
        return redirect(url_for('index.index_view'))
    except Exception as e:
        return f"操作失败: {str(e)}", 500
