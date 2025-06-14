import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, ActuatorStatus

app = create_app()

with app.app_context():
    print("Criando todas as tabelas no banco de dados...")
    db.create_all()
    print("Tabelas criadas com sucesso.")

    print("Criando usuário 'admin' inicial...")
    if User.query.filter_by(username='admin').first() is None:
        admin_user = User(
            username='admin',
            full_name='Administrador do Sistema',
            email='admin@example.com',
            role='admin'
        )
        admin_user.set_password('admin') 
        db.session.add(admin_user)
        db.session.commit()
        print("Usuário 'admin' criado.")
    else:
        print("Usuário 'admin' já existe.")

    print("Criando registros de atuadores iniciais...")
    actuators = ['aquecedor', 'ventilador', 'cortina', 'aspersor']
    for act_name in actuators:
        if not ActuatorStatus.query.filter_by(actuator_name=act_name).first():
            actuator = ActuatorStatus(actuator_name=act_name, status='desligado')
            db.session.add(actuator)
    
    db.session.commit()
    print("Registros de atuadores criados.")