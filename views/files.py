from flask import Blueprint, render_template, request, jsonify, send_file, session
from auth import login_required
from utils import validate_user_container, get_container_name, load_config
from models import DockerManager
import os
import subprocess
import tempfile
import shutil
from werkzeug.utils import secure_filename

files = Blueprint('files', __name__, url_prefix='/files')
docker_manager = DockerManager()

@files.route('/')
@login_required
def files_view():
    """文件管理页面"""
    try:
        container_id = request.args.get('container_id')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        return render_template('files/files.html',
                             container_id=container_id,
                             user=session['user'])
    except Exception as e:
        return f"加载文件管理失败: {str(e)}", 500

@files.route('/list')
@login_required
def list_files():
    """列出目录内容"""
    try:
        container_id = request.args.get('container_id')
        path = request.args.get('path', '/data')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return jsonify({'error': '无权操作此容器'}), 403
            
        # 获取容器信息
        container_name = get_container_name(int(container_id))
        
        # 列出目录内容
        cmd = ['sudo', 'docker', 'exec', container_name, 'ls', '-la', path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({'error': '获取目录列表失败'}), 500
            
        # 解析ls输出
        files = []
        for line in result.stdout.strip().split('\n')[1:]:  # 跳过第一行(total)
            parts = line.split()
            if len(parts) >= 9:
                name = ' '.join(parts[8:])
                if name not in ['.', '..']:
                    files.append({
                        'name': name,
                        'type': 'd' if parts[0].startswith('d') else 'f',
                        'size': parts[4],
                        'permissions': parts[0],
                        'owner': parts[2],
                        'group': parts[3],
                        'modified': ' '.join(parts[5:8])
                    })
        
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files.route('/download')
@login_required
def download_file():
    """下载文件"""
    try:
        container_id = request.args.get('container_id')
        path = request.args.get('path')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return "无权操作此容器", 403
            
        # 获取容器信息
        container_name = get_container_name(int(container_id))
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            # 从容器复制文件
            cmd = ['sudo', 'docker', 'cp', f'{container_name}:{path}', temp.name]
            result = subprocess.run(cmd)
            
            if result.returncode != 0:
                return "下载文件失败", 500
            
            # 发送文件
            return send_file(
                temp.name,
                as_attachment=True,
                download_name=os.path.basename(path)
            )
    except Exception as e:
        return f"下载文件失败: {str(e)}", 500

@files.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """上传文件"""
    try:
        container_id = request.form.get('container_id')
        path = request.form.get('path', '/data')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return jsonify({'error': '无权操作此容器'}), 403
            
        if 'file' not in request.files:
            return jsonify({'error': '没有上传文件'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
            
        # 获取容器信息
        container_name = get_container_name(int(container_id))
        
        # 保存文件到临时目录
        filename = secure_filename(file.filename)
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            file.save(temp.name)
            
            # 复制文件到容器
            target_path = os.path.join(path, filename)
            cmd = ['sudo', 'docker', 'cp', temp.name, f'{container_name}:{target_path}']
            result = subprocess.run(cmd)
            
            if result.returncode != 0:
                return jsonify({'error': '上传文件失败'}), 500
            
            # 设置文件权限
            cmd = ['sudo', 'docker', 'exec', container_name, 'chmod', '644', target_path]
            subprocess.run(cmd)
            
        return jsonify({'message': '文件上传成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files.route('/create_folder', methods=['POST'])
@login_required
def create_folder():
    """创建文件夹"""
    try:
        container_id = request.form.get('container_id')
        path = request.form.get('path')
        name = request.form.get('name')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return jsonify({'error': '无权操作此容器'}), 403
            
        # 获取容器信息
        container_name = get_container_name(int(container_id))
        
        # 创建文件夹
        folder_path = os.path.join(path, name)
        cmd = ['sudo', 'docker', 'exec', container_name, 'mkdir', '-p', folder_path]
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            return jsonify({'error': '创建文件夹失败'}), 500
            
        return jsonify({'message': '文件夹创建成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files.route('/delete', methods=['POST'])
@login_required
def delete_item():
    """删除文件或文件夹"""
    try:
        container_id = request.form.get('container_id')
        path = request.form.get('path')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return jsonify({'error': '无权操作此容器'}), 403
            
        # 获取容器信息
        container_name = get_container_name(int(container_id))
        
        # 删除文件或文件夹
        cmd = ['sudo', 'docker', 'exec', container_name, 'rm', '-rf', path]
        result = subprocess.run(cmd)
        
        if result.returncode != 0:
            return jsonify({'error': '删除失败'}), 500
            
        return jsonify({'message': '删除成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files.route('/read', methods=['GET'])
@login_required
def read_file():
    """读取文件内容"""
    try:
        container_id = request.args.get('container_id')
        path = request.args.get('path')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return jsonify({'error': '无权操作此容器'}), 403
            
        # 获取容器信息
        container_name = get_container_name(int(container_id))
        
        # 读取文件内容
        cmd = ['sudo', 'docker', 'exec', container_name, 'cat', path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({'error': '读取文件失败'}), 500
            
        return jsonify({'content': result.stdout})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@files.route('/write', methods=['POST'])
@login_required
def write_file():
    """写入文件内容"""
    try:
        container_id = request.form.get('container_id')
        path = request.form.get('path')
        content = request.form.get('content')
        user_id = str(session['user']['id'])
        
        # 验证容器所有权
        config = load_config()
        if not validate_user_container(config, container_id, user_id):
            return jsonify({'error': '无权操作此容器'}), 403
            
        # 获取容器信息
        container_name = get_container_name(int(container_id))
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp:
            temp.write(content)
            
        # 复制文件到容器
        cmd = ['sudo', 'docker', 'cp', temp.name, f'{container_name}:{path}']
        result = subprocess.run(cmd)
        
        # 删除临时文件
        os.unlink(temp.name)
        
        if result.returncode != 0:
            return jsonify({'error': '写入文件失败'}), 500
            
        return jsonify({'message': '保存成功'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
