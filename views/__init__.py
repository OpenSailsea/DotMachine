def init_views(app):
    """初始化所有视图"""
    # 延迟导入视图函数，避免循环导入
    def register_blueprint(module_name, blueprint_name):
        module = __import__(f'views.{module_name}', fromlist=[blueprint_name])
        blueprint = getattr(module, blueprint_name)
        app.register_blueprint(blueprint)
    
    # 按顺序注册蓝图
    register_blueprint('index', 'index')
    register_blueprint('instance', 'instance')
    register_blueprint('website', 'website')
    register_blueprint('system', 'system')
    register_blueprint('terminal', 'terminal')
    register_blueprint('files', 'files')
