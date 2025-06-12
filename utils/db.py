# utils/db.py
import sys
import os

# Adiciona o diretório raiz ao path para encontrar o módulo 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, User, ActuatorStatus, SystemSettings

app = create_app()

with app.app_context():
    print("Criando todas as tabelas no banco de dados...")
    db.create_all()
    print("Tabelas criadas com sucesso.")

    # Opcional: Criar um usuário admin inicial
    if not User.query.filter_by(username='admin').first():
        print("Criando usuário 'admin' inicial...")
        admin = User(
            username='admin',
            full_name='Administrador do Sistema',
            email='admin@sistema.com',
            role='admin'
        )
        admin.set_password('admin123') # Troque essa senha!
        db.session.add(admin)
        db.session.commit()
        print("Usuário 'admin' criado.")

    # Opcional: Criar registros iniciais para atuadores e configurações
    actuators = ['aquecedor', 'ventilador', 'nevoa', 'persiana']
    for act_name in actuators:
        if not ActuatorStatus.query.filter_by(name=act_name).first():
            actuator = ActuatorStatus(name=act_name)
            db.session.add(actuator)
    
    settings = {'temp_muito_frio': 10.0, 'temp_frio': 15.0, 'temp_quente': 25.0, 'temp_muito_quente': 30.0}
    for key, value in settings.items():
        if not SystemSettings.query.filter_by(setting_name=key).first():
            setting = SystemSettings(setting_name=key, value=value)
            db.session.add(setting)

    db.session.commit()
    print("Registros iniciais de atuadores e configurações criados.")