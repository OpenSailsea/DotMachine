def init_views(app):
    """初始化所有视图"""
    # 导入视图函数
    from . import vps as vps_views
    from . import website as website_views
    from . import system as system_views
    from . import index as index_views
    
    # 注册蓝图
    app.register_blueprint(vps_views.vps)
    app.register_blueprint(website_views.website)
    app.register_blueprint(system_views.system)
    app.register_blueprint(index_views.index)
