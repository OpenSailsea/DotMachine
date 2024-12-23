from flask import render_template, session
from auth import login_required
from utils import load_config, calculate_machine_stats, get_remaining_time, format_container_info

from flask import Blueprint

index = Blueprint('index', __name__)

@index.route('/')
@login_required
def index_view():
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
        
        # 计算机器统计信息
        machine_stats = calculate_machine_stats(config)
        
        # 计算容器剩余时间
        remaining_time = {'days': 0, 'hours': 0, 'total_hours': 0}
        if user_container and 'expires_at' in user_container:
            remaining_time = get_remaining_time(user_container['expires_at'])
        
        # 格式化容器信息
        if user_container:
            user_container = format_container_info(user_container)
        
        return render_template('index.html',
            user=session['user'], 
            user_container=user_container, 
            container_id=container_id,
            machine_stats=machine_stats,
            remaining_time=remaining_time)
