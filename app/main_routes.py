# app/main_routes.py
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from .models import SensorData, db # Vamos precisar de SensorData e db para o log
from .mqtt_utils import get_current_status # Importa nossa nova função
from datetime import datetime
from .models import ActuatorStatus
from flask import request, jsonify
from .mqtt_utils import publish_command


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

@bp.route('/atuadores')
@login_required
def atuadores():
    # 1. Busca o status atual em tempo real do broker MQTT
    live_status = get_current_status()

    # 2. Busca o histórico (última ativação) do nosso banco de dados
    actuators_from_db = ActuatorStatus.query.all()
    history_status = {act.name: act.last_changed.strftime('%d/%m/%Y às %H:%M:%S') for act in actuators_from_db}

    # 3. Mapeia os nomes para a exibição na interface
    actuator_display_names = {
        'heater': 'Aquecedor',
        'fan': 'Ventilador',
        'mist': 'Sistema de Névoa',
        'pers': 'Persiana'
    }
    
    return render_template('atuadores.html', 
                           title='Atuadores', 
                           live_status=live_status, 
                           history_status=history_status,
                           actuator_names=actuator_display_names)

@bp.route('/atuador/command', methods=['POST'])
@login_required
def atuador_command():
    if current_user.role != 'admin':
        return jsonify({'status': 'error', 'message': 'Não autorizado'}), 403

    data = request.get_json()
    actuator = data.get('actuator')
    command = data.get('command')

    # Mapa de chaves da interface para tópicos de comando MQTT
    command_topic_map = {
        'heater': 'bezerros/heater/command',
        'fan': 'bezerros/fan/command',
        'mist': 'bezerros/mist/command',
        'pers': 'bezerros/pers/command'
    }

    topic = command_topic_map.get(actuator)

    if not topic or command not in ['0', '1']:
        return jsonify({'status': 'error', 'message': 'Comando ou atuador inválido'}), 400

    success = publish_command(topic, command)

    if success:
        return jsonify({'status': 'success', 'message': f'Comando {command} enviado para {actuator}.'})
    else:
        return jsonify({'status': 'error', 'message': 'Falha ao publicar no broker MQTT.'}), 500