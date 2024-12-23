def init_views(app):
    """初始化所有视图"""
    # 导入视图函数
    from . import instance as instance_views
    from . import website as website_views
    from . import system as system_views
    from . import index as index_views
    from . import terminal as terminal_views
    from . import files as files_views
    
    # 注册蓝图
    app.register_blueprint(instance_views.instance)
    app.register_blueprint(website_views.website)
    app.register_blueprint(system_views.system)
    app.register_blueprint(index_views.index)
    app.register_blueprint(terminal_views.terminal)
    app.register_blueprint(files_views.files)
