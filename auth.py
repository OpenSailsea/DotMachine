from functools import wraps
from flask import session, redirect, url_for, render_template_string
from requests_oauthlib import OAuth2Session
import os
from config import (
    CLIENT_ID, 
    CLIENT_SECRET,
    REDIRECT_URI,
    AUTH_BASE_URL,
    TOKEN_URL,
    USER_INFO_URL
)

# 允许 OAuth2 使用 HTTP (仅用于开发环境)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('auth.login'))
        if session['user'].get('trust_level', 0) < 2:
            return render_template_string("""
                <h1>权限不足</h1>
                <p>需要信任等级 2 以上的用户才能访问此功能。</p>
                <p>您当前的信任等级: {{ trust_level }}</p>
                <p><a href="/logout">退出登录</a></p>
            """, trust_level=session['user'].get('trust_level', 0))
        return f(*args, **kwargs)
    return decorated_function

def get_oauth_session(state=None):
    """获取OAuth会话"""
    return OAuth2Session(
        CLIENT_ID,
        redirect_uri=REDIRECT_URI,
        state=state
    )

def get_authorization_url():
    """获取授权URL"""
    oauth = get_oauth_session()
    authorization_url, state = oauth.authorization_url(AUTH_BASE_URL)
    return authorization_url, state

def fetch_token(oauth, response_url):
    """获取访问令牌"""
    return oauth.fetch_token(
        TOKEN_URL,
        client_secret=CLIENT_SECRET,
        authorization_response=response_url
    )

def get_user_info(oauth):
    """获取用户信息"""
    return oauth.get(USER_INFO_URL).json()

class AuthError(Exception):
    """认证错误"""
    pass

def verify_user_permission(user_info, required_level=2):
    """验证用户权限"""
    trust_level = user_info.get('trust_level', 0)
    if trust_level < required_level:
        raise AuthError(f"需要信任等级 {required_level} 以上的用户才能访问此功能")
    return True

def init_auth_routes(app):
    """初始化认证相关路由"""
    from flask import Blueprint, request
    
    auth = Blueprint('auth', __name__)
    
    @auth.route('/login')
    def login():
        authorization_url, state = get_authorization_url()
        session['oauth_state'] = state
        return redirect(authorization_url)
    
    @auth.route('/oauth2/callback')
    def callback():
        try:
            oauth = get_oauth_session(state=session.get('oauth_state'))
            token = fetch_token(oauth, request.url)
            user_info = get_user_info(oauth)
            
            session['user'] = user_info
            session['oauth_token'] = token
            
            return redirect(url_for('index.index_view'))
        except Exception as e:
            return render_template_string("""
                <h1>登录失败</h1>
                <p>{{ error }}</p>
                <p><a href="/login">重试</a></p>
            """, error=str(e))
    
    @auth.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for('index.index_view'))
    
    app.register_blueprint(auth)
