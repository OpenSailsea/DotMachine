from flask import Blueprint, request, redirect, url_for, render_template, session
from auth import login_required
from models import ContainerManager
from utils import validate_user_container

vps = Blueprint('vps', __name__, url_prefix='/vps')
container_manager = ContainerManager()

@vps.route('/create', methods=['POST'])
@login_required
def create():
    """创建VPS"""
    try:
        container_type = request.form.get('type', 'base')
        user_id = str(session['user']['id'])
        username = f"dotm-{session['user']['username']}"
        
        # 创建容器
        container_info, password = container_manager.create_container(
            user_id=user_id,
            username=username,
            container_type=container_type
        )
        
        return render_template('vps/success.html',
            username=container_info['username'],
            password=password,
            ssh_port=container_info['ssh_port'],
            ftp_port=container_info['ftp_port'],
            http_port=container_info['http_port'],
            user=session['user'],
            user_container=True
        )
            
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        return f"创建VPS失败: {str(e)}", 500

@vps.route('/remove', methods=['POST'])
@login_required
def remove():
    """删除VPS"""
    try:
        container_id = request.form.get('container_id')
        user_id = str(session['user']['id'])
        
        # 删除容器
        container_manager.remove_container(container_id, user_id)
        
        return redirect(url_for('index.index_view'))
    except ValueError as e:
        return str(e), 403
    except Exception as e:
        return f"删除VPS失败: {str(e)}", 500

@vps.route('/renew', methods=['POST'])
@login_required
def renew():
    """续期VPS"""
    try:
        from datetime import datetime, timedelta
        from utils import load_config, save_config, calculate_expiry
        
        container_id = request.form.get('container_id')
        user_id = str(session['user']['id'])
        
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        container_info = config['containers'][container_id]
        
        # 计算新的过期时间
        expires_at_str = container_info['expires_at'].rstrip('Z').split('.')[0]
        expires_at = datetime.strptime(expires_at_str, '%Y-%m-%dT%H:%M:%S')
        now = datetime.utcnow()
        
        # 如果已过期，从当前时间开始计算
        if expires_at < now:
            new_expires_at = calculate_expiry(days=5)
        else:
            # 如果未过期，从原有期限开始追加
            new_expires_at = calculate_expiry(days=5, from_date=expires_at)
            
        config['containers'][container_id]['expires_at'] = new_expires_at
        save_config(config)
        
        return redirect(url_for('index.index_view'))
    except Exception as e:
        return f"续期失败: {str(e)}", 500
