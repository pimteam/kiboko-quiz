import os 

from flask import Flask
from flask_wtf.csrf import CSRFProtect

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'quiz.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    csrf = CSRFProtect(app)   
        
    from . import db
    db.init_app(app)
    
    from . import auth
    app.register_blueprint(auth.bp)
    
    from . import quizzes
    app.register_blueprint(quizzes.bp)
    app.add_url_rule('/', endpoint='index')
    app.add_url_rule('/create', endpoint='create')
    
    from . import admin
    app.register_blueprint(admin.bp)
    app.add_url_rule('/admin/', endpoint='index')
    
    from . import admin_quizzes
    app.register_blueprint(admin_quizzes.bp)
    app.add_url_rule('/admin/quiz/', endpoint='index')
    
    from . import admin_grades
    app.register_blueprint(admin_grades.bp)
    app.add_url_rule('/admin/grades/', endpoint='grades')
    
    from . import admin_results
    app.register_blueprint(admin_results.bp)
    app.add_url_rule('/admin/results/', endpoint='index')

    return app