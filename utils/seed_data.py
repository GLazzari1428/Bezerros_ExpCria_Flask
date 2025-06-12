# utils/seed_data.py
import sys
import os
import random
import math
from datetime import datetime, timedelta

# Adiciona o diretório raiz ao path para encontrar o módulo 'app'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models import db, SensorData

app = create_app()

with app.app_context():
    # Verifica se já existem dados para não popular duas vezes
    if SensorData.query.count() > 50: # Se tiver mais de 50 registros, não faz nada
        print("O banco de dados de sensores já parece estar populado. Saindo.")
        exit()

    print("Populando o banco de dados com dados de sensores fictícios dos últimos 30 dias...")
    
    end_time = datetime.now()
    # Gera 30 dias de dados, um a cada 30 minutos
    total_points = 30 * 24 * 2 
    
    new_data_points = []
    for i in range(total_points):
        # Calcula o timestamp para este ponto, indo para trás no tempo
        current_time = end_time - timedelta(minutes=i * 30)
        
        # Gera uma temperatura com padrão senoidal (mais frio de madrugada, mais quente de tarde)
        # e um pouco de ruído aleatório
        temp_variation = math.sin(i / (24 * 2) * math.pi) * 10  # Variação de 10 graus
        temperature = 18 + temp_variation + random.uniform(-1.5, 1.5)
        
        # Gera uma umidade aleatória
        humidity = random.uniform(40.0, 85.0)

        data_point = SensorData(
            temperature=round(temperature, 2),
            humidity=round(humidity, 2),
            timestamp=current_time
        )
        new_data_points.append(data_point)

    # Adiciona todos os pontos de uma vez (muito mais eficiente)
    db.session.bulk_save_objects(new_data_points)
    db.session.commit()
    
    print(f"Sucesso! {total_points} pontos de dados fictícios foram adicionados ao banco.")