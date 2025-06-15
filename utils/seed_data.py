# utils/seed_data.py
import sys
import os
import random
import math
from datetime import datetime, timedelta, date

# --- CORREÇÃO AQUI ---
# Adiciona o diretório raiz do projeto ao caminho do Python
# Isso deve vir ANTES de importar qualquer módulo do seu app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Agora as importações do projeto funcionarão
from app import create_app
from app.models import db, SensorData, User, Bezerro, ActuatorHistory


app = create_app()

with app.app_context():

    print("Verificando e criando usuários administradores fictícios...")
    
    admin_usernames = ['ana_silva', 'bruno_costa', 'carla_dias', 'diego_souza', 'elisa_pereira']
    new_admins = []

    main_admin = User.query.filter_by(username='admin').first()
    if not main_admin:
        print("Usuário 'admin' principal não encontrado. Por favor, execute 'utils/db.py' primeiro.")
        exit()

    for username in admin_usernames:
        if User.query.filter_by(username=username).first() is None:
            admin_user = User(
                username=username,
                full_name=f'{username.replace("_", " ").title()}',
                email=f'{username}@example.com',
                role='admin'
            )
            admin_user.set_password('12345')
            db.session.add(admin_user)
            new_admins.append(admin_user)
            print(f"Usuário '{username}' criado.")
        else:
            new_admins.append(User.query.filter_by(username=username).first())
            print(f"Usuário '{username}' já existe.")
    
    db.session.commit()
    print("Criação de usuários finalizada.")

    print("\nPopulando o banco de dados com bezerros fictícios...")


    bezerros_para_criar = []
    bezerro_num = 1
    for admin in new_admins:
        for i in range(4):
            bezerro = Bezerro(
                nome=f'Mimoso {bezerro_num}',
                sexo=random.choice(['Macho', 'Fêmea']),
                data_nascimento=date.today() - timedelta(days=random.randint(10, 365)),
                criado_por_id=admin.id
            )
            bezerros_para_criar.append(bezerro)
            bezerro_num += 1
    
    for i in range(10):
        bezerro = Bezerro(
            nome=f'Pintado {bezerro_num}',
            sexo=random.choice(['Macho', 'Fêmea']),
            data_nascimento=date.today() - timedelta(days=random.randint(10, 365)),
            criado_por_id=main_admin.id
        )
        bezerros_para_criar.append(bezerro)
        bezerro_num += 1

    db.session.bulk_save_objects(bezerros_para_criar)
    db.session.commit()
    print(f"Sucesso! {len(bezerros_para_criar)} bezerros fictícios foram adicionados.")


    print("\nPopulando o banco de dados com dados de sensores fictícios...")
    if SensorData.query.count() > 50:
        print("O banco de dados de sensores já parece estar populado. Saindo da seção de sensores.")
    else:
        end_time = datetime.now()
        total_points = 30 * 24 * 2 
        
        new_data_points = []
        for i in range(total_points):
            current_time = end_time - timedelta(minutes=i * 30)
            temp_variation = math.sin(i / (24 * 2) * math.pi) * 10
            temperature = 18 + temp_variation + random.uniform(-1.5, 1.5)
            humidity = random.uniform(40.0, 85.0)

            data_point = SensorData(
                temperature=round(temperature, 2),
                humidity=round(humidity, 2),
                timestamp=current_time
            )
            new_data_points.append(data_point)

        db.session.bulk_save_objects(new_data_points)
        db.session.commit()
        print(f"Sucesso! {total_points} pontos de dados de sensores fictícios foram adicionados.")

    print("\nPopulando o banco de dados com histórico de atuadores fictício...")
    if ActuatorHistory.query.count() > 0:
        print("O banco de dados de histórico de atuadores já parece estar populado. Pulando esta etapa.")
    else:
        new_history_logs = []
        actuator_names = ['Aquecedor', 'Ventilador', 'Sistema de Névoa', 'Persiana']
        end_time = datetime.now()

        # Gera eventos aleatórios para as últimas 72 horas
        for i in range(72):
            # Chance de 60% de ocorrer um evento a cada hora
            if random.random() < 0.6:
                current_time = end_time - timedelta(hours=i, minutes=random.randint(0, 59))
                actuator = random.choice(actuator_names)

                if actuator == 'Persiana':
                    status = random.choice(['aberto', 'fechado'])
                else:
                    status = random.choice(['ligado', 'desligado'])
                
                log_entry = ActuatorHistory(
                    actuator_name=actuator,
                    status=status,
                    timestamp=current_time
                )
                new_history_logs.append(log_entry)

        if new_history_logs:
            db.session.bulk_save_objects(new_history_logs)
            db.session.commit()
        
        print(f"Sucesso! {len(new_history_logs)} registros de histórico de atuadores foram adicionados.")


print("\nProcesso de 'seeding' concluído.")