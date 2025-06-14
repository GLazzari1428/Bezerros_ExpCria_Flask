# app/__init__.py

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
# Redireciona para a página de login se o usuário tentar acessar uma página protegida
login_manager.login_view = 'auth.login' 
login_manager.login_message = None

def create_app(config_class=Config):
    """
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)

    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from .main_routes import bp as main_bp
    app.register_blueprint(main_bp)

    from . import models

    return app