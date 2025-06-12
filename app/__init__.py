# app/__init__.py
from flask import Flask
from config import Config
from .models import db
from flask_login import LoginManager

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializa o DB
    db.init_app(app)

    # Inicializa o Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login' # Rota para a qual usuários não logados são redirecionados
    login_manager.init_app(app)

    from .models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Registra os Blueprints (nossas "áreas" do site)
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # (Adicionaremos mais blueprints aqui depois)

    return app