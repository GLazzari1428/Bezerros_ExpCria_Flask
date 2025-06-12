# utils/db.py

import sys
import os

# Adiciona o diretório raiz do projeto ao path do Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, ActuatorStatus

# Cria uma instância da aplicação para obter o contexto da aplicação
app = create_app()

# O 'with app.app_context()' garante que a aplicação esteja configurada
# corretamente antes de interagir com o banco de dados.
with app.app_context():
    print("Criando todas as tabelas no banco de dados...")
    # Cria todas as tabelas definidas nos seus modelos
    db.create_all()
    print("Tabelas criadas com sucesso.")

    print("Criando usuário 'admin' inicial...")
    # Verifica se o usuário admin já existe
    if User.query.filter_by(username='admin').first() is None:
        admin_user = User(
            username='admin',
            full_name='Administrador do Sistema',
            email='admin@example.com',
            role='admin'
        )
        admin_user.set_password('admin')  # Defina uma senha segura aqui
        db.session.add(admin_user)
        db.session.commit()
        print("Usuário 'admin' criado.")
    else:
        print("Usuário 'admin' já existe.")

    # Adiciona os atuadores iniciais se eles não existirem
    print("Criando registros de atuadores iniciais...")
    actuators = ['aquecedor', 'ventilador', 'cortina', 'aspersor']
    for act_name in actuators:
        if not ActuatorStatus.query.filter_by(actuator_name=act_name).first():
            actuator = ActuatorStatus(actuator_name=act_name, status='desligado')
            db.session.add(actuator)
    
    db.session.commit()
    print("Registros de atuadores criados.")