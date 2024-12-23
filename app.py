from flask import Flask
from config import SECRET_KEY, DEBUG, HOST, PORT
from auth import init_auth_routes
from views import init_views
import os
from asgiref.wsgi import WsgiToAsgi  # 用于将 WSGI 转换为 ASGI
from extensions import socketio

def create_app():
    """创建并配置Flask应用"""
    app = Flask(__name__)
    
    # 基本配置
    app.secret_key = SECRET_KEY
    app.debug = DEBUG
    
    # 确保静态资源目录存在
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # 初始化认证路由
    init_auth_routes(app)
    
    # 初始化视图路由
    init_views(app)
    
    # 打印所有路由
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    
    # 初始化SocketIO
    socketio.init_app(app, cors_allowed_origins="*")
    
    return app

# 将 Flask 应用转换为 ASGI 应用
asgi_app = WsgiToAsgi(create_app())

def main():
    """主函数"""
    app = create_app()
    socketio.run(app, host=HOST, port=PORT)

if __name__ == '__main__':
    main()
