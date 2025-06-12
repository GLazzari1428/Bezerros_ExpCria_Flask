# app/models.py

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
# A importação agora vai funcionar porque o 'db' em __init__.py é criado antes.
from . import db, login_manager

# O Flask-Login precisa desta função para saber como encontrar um usuário pelo ID.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Adicionamos 'UserMixin' para integrar o modelo User com o Flask-Login
class User(UserMixin, db.Model):
    # O 'id' já é a chave primária, o Flask-Login vai usá-lo.
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    full_name = db.Column(db.String(120))
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default='publico_geral') # 'admin' ou 'publico_geral'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_all():
        return User.query.all()

    @staticmethod
    def get_by_id(id):
        return User.query.get(id)


class SensorData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temperature = db.Column(db.Float)
    humidity = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, index=True, default=db.func.now())

class ActuatorStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    actuator_name = db.Column(db.String(50), unique=True)
    status = db.Column(db.String(20))
    last_changed = db.Column(db.DateTime, default=db.func.now())

class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    temp_frio = db.Column(db.Float, default=15.0)
    temp_quente = db.Column(db.Float, default=25.0)
    umidade_baixa = db.Column(db.Float, default=40.0) 
    umidade_alta = db.Column(db.Float, default=60.0)

    @classmethod
    def get_settings(cls):
        settings = cls.query.first()
        if not settings:
            settings = cls()
            db.session.add(settings)
            db.session.commit()
        return settings