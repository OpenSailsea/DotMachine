from flask_socketio import SocketIO

# 创建SocketIO实例
socketio = SocketIO(async_mode="eventlet")  # 注意 async_mode 必须为 "asgi"
