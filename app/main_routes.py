# app/main_routes.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .models import SensorData, db # Vamos precisar de SensorData e db para o log
from .mqtt_utils import get_current_status # Importa nossa nova função
from datetime import datetime

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/home')
@login_required
def home():
    # Chama nossa função para buscar os dados mais recentes do MQTT
    status = get_current_status()
    
    # Processa os dados recebidos (com valores padrão caso algo falhe)
    temp_atual_str = status.get('temperature', 'N/A')
    umid_atual_str = status.get('umidade', 'N/A')

    # --- Lógica de log de dados ---
    # Se temos dados válidos, salvamos no banco para o histórico
    try:
        temp_val = float(temp_atual_str)
        umid_val = float(umid_atual_str)
        
        # Cria e salva o registro no banco
        new_log = SensorData(temperature=temp_val, humidity=umid_val, timestamp=datetime.now())
        db.session.add(new_log)
        db.session.commit()
    except (ValueError, TypeError):
        print("Não foi possível salvar o log: dados de sensor inválidos ou ausentes.")

    # Lógica para definir a cor e o status na interface
    status_geral = "Indisponível"
    status_cor = "secondary"
    try:
        temp = float(temp_atual_str)
        if temp >= 30.0:
            status_geral = "Muito Quente"
            status_cor = "danger"
        elif temp >= 25.0:
            status_geral = "Quente"
            status_cor = "warning"
        elif temp < 15.0:
            status_geral = "Frio"
            status_cor = "info"
        elif temp < 10.0:
            status_geral = "Muito Frio"
            status_cor = "primary"
        else:
            status_geral = "Normal"
            status_cor = "success"
    except (ValueError, TypeError):
        pass # Mantém o status como "Indisponível"
            
    return render_template('home.html', 
                           title='Home', 
                           status_geral=status_geral, 
                           status_cor=status_cor,
                           temp_atual=temp_atual_str,
                           umid_atual=umid_atual_str)