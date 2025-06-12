# app/__init__.py

from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# 1. Instancie as extensões aqui, sem vincular a uma 'app' ainda.
db = SQLAlchemy()
login_manager = LoginManager()
# Redireciona para a página de login se o usuário tentar acessar uma página protegida
login_manager.login_view = 'auth.login' 

def create_app(config_class=Config):
    """
    Fábrica de aplicação: cria e configura a instância do Flask.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 2. Inicialize as extensões com a instância da aplicação.
    db.init_app(app)
    login_manager.init_app(app)

    # 3. Registre os Blueprints (as áreas do nosso site).
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    from .main_routes import bp as main_bp
    app.register_blueprint(main_bp)

    # É importante que os modelos sejam "vistos" pela aplicação.
    # Esta linha garante que o user_loader do Flask-Login seja registrado.
    from . import models

    return app