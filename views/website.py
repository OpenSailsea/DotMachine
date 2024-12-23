from flask import Blueprint, request, redirect, url_for, render_template, session
from auth import login_required
from models import DockerManager
from utils import (
    validate_domain,
    validate_user_container,
    get_container_name,
    load_config,
    save_config
)

website = Blueprint('website', __name__, url_prefix='/website')
docker_manager = DockerManager()

@website.route('/add', methods=['POST'])
@login_required
def add():
    """添加网站"""
    try:
        container_id = request.form.get('container_id')
        domain = request.form.get('domain')
        user_id = str(session['user']['id'])
        
        # 验证域名格式
        if not validate_domain(domain):
            return "无效的域名格式", 400
            
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        # 获取容器
        container_name = get_container_name(int(container_id))
        container = docker_manager.get_container(container_name)
        if not container:
            return "容器不存在", 404
            
        # 在容器中创建网站配置
        result = container.exec_run(['/usr/local/bin/generate_nginx_config.sh', domain])
        if result.exit_code != 0:
            return f"创建网站配置失败: {result.output.decode()}", 500
            
        # 更新配置
        if 'websites' not in config['containers'][container_id]:
            config['containers'][container_id]['websites'] = []
        if domain not in config['containers'][container_id]['websites']:
            config['containers'][container_id]['websites'].append(domain)
            save_config(config)
        
        return redirect(url_for('index.index_view'))
    except Exception as e:
        return f"添加网站失败: {str(e)}", 500

@website.route('/remove', methods=['POST'])
@login_required
def remove():
    """删除网站"""
    try:
        container_id = request.form.get('container_id')
        domain = request.form.get('domain')
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
            
        # 删除网站配置和目录
        container.exec_run(['rm', '-f', f'/etc/nginx/sites-enabled/{domain}.conf'])
        container.exec_run(['rm', '-rf', f'/data/www/{domain}'])
        container.exec_run(['nginx', '-s', 'reload'])
        
        # 更新配置
        if 'websites' in config['containers'][container_id]:
            if domain in config['containers'][container_id]['websites']:
                config['containers'][container_id]['websites'].remove(domain)
                save_config(config)
        
        return redirect(url_for('index.index_view'))
    except Exception as e:
        return f"删除网站失败: {str(e)}", 500

@website.route('/list', methods=['GET'])
@login_required
def list_websites():
    """列出网站"""
    try:
        container_id = request.args.get('container_id')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        # 获取网站列表
        websites = config['containers'][container_id].get('websites', [])
        
        return render_template('website/list.html', 
                             websites=websites, 
                             container_id=container_id,
                             user=session['user'],
                             user_container=True)
    except Exception as e:
        return f"获取网站列表失败: {str(e)}", 500
