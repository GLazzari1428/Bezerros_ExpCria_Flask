from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from .models import SensorData, db
from .mqtt_utils import get_current_status
from datetime import datetime
from .models import ActuatorStatus, User, SystemSettings, Bezerro, ActuatorHistory
from .forms import RegistrationForm, EditUserForm, SettingsForm, BezerroForm
from flask import request, jsonify
from .mqtt_utils import publish_command
from datetime import datetime, timedelta
from sqlalchemy import func
from . import mqtt_utils

bp = Blueprint('main', __name__)

# app/main_routes.py

@bp.route('/')
@bp.route('/home')
@login_required
def home():
    settings = SystemSettings.get_settings()

    muito_quente_threshold = settings.temp_quente + 5.0
    muito_frio_threshold = settings.temp_frio - 5.0

    status = get_current_status()
    
    temp_atual_str = status.get('temperature', 'N/A')
    umid_atual_str = status.get('umidade', 'N/A')

    try:
        temp_val = float(temp_atual_str)
        umid_val = float(umid_atual_str)
        
        new_log = SensorData(temperature=temp_val, humidity=umid_val, timestamp=datetime.now())
        db.session.add(new_log)
        db.session.commit()
    except (ValueError, TypeError):
        print("Não foi possível salvar o log: dados de sensor inválidos ou ausentes.")

    status_geral = "Indisponível"
    status_cor = "secondary"
    
    try:
        temp = float(temp_atual_str)
        if temp >= muito_quente_threshold:
            status_geral = "Muito Quente"
            status_cor = "danger"
        elif temp >= settings.temp_quente:
            status_geral = "Quente"
            status_cor = "warning"
        elif temp < muito_frio_threshold:
            status_geral = "Muito Frio"
            status_cor = "primary"
        elif temp < settings.temp_frio:
            status_geral = "Frio"
            status_cor = "info"
        else:
            status_geral = "Normal"
            status_cor = "success"
    except (ValueError, TypeError):
        pass 
            
    return render_template('home.html', 
                           title='Home', 
                           status_geral=status_geral, 
                           status_cor=status_cor,
                           temp_atual=temp_atual_str,
                           umid_atual=umid_atual_str)

@bp.route('/atuadores')
@login_required
def atuadores():

    live_status = get_current_status()


    actuators_from_db = ActuatorStatus.query.all()
    history_status = {act.actuator_name: act.last_changed.strftime('%d/%m/%Y às %H:%M:%S') for act in actuators_from_db}

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
        try:
            status_text = "aberto" if command == '1' and actuator == 'pers' else \
                          "fechado" if command == '0' and actuator == 'pers' else \
                          "ligado" if command == '1' else "desligado"
            
            history_log = ActuatorHistory(
                actuator_name=actuator_display_names.get(actuator, actuator),
                status=status_text,
                timestamp=datetime.now()
            )
            db.session.add(history_log)
            db.session.commit()
        except Exception as e:
            print(f"Erro ao salvar histórico do atuador: {e}")
            # Não impede a resposta de sucesso, apenas loga o erro no servidor
        return jsonify({'status': 'success', 'message': f'Comando {command} enviado para {actuator}.'})
    else:
        return jsonify({'status': 'error', 'message': 'Falha ao publicar no broker MQTT.'}), 500

@bp.route('/sensores')
@login_required
def sensores():
    status = get_current_status()
    temp_atual = status.get('temperature', 'N/A')
    umid_atual = status.get('umidade', 'N/A')
    return render_template('sensores.html', 
                           title='Sensores',
                           temp_atual=temp_atual,
                           umid_atual=umid_atual)

@bp.route('/api/sensor_data/<periodo>')
@login_required
def sensor_data(periodo):
    end_time = datetime.now()
    query_result = []
    
    if periodo == '1h':
        start_time = end_time - timedelta(hours=1)
        query_result = SensorData.query.filter(SensorData.timestamp.between(start_time, end_time)).order_by(SensorData.timestamp.asc()).all()
        labels = [d.timestamp.strftime('%H:%M') for d in query_result]
        temperatures = [d.temperature for d in query_result]
        humidities = [d.humidity for d in query_result]

    else:

        date_format_mysql = "" 
        label_format_python = "" 

        if periodo == '12h':
            start_time = end_time - timedelta(hours=12)
            date_format_mysql = '%Y-%m-%d %H:%i'
            label_format_python = '%H:%M'
        elif periodo == '24h':
            start_time = end_time - timedelta(days=1)
            date_format_mysql = '%Y-%m-%d %H:00' 
            label_format_python = '%d/%m %Hh'
        elif periodo == '7d':
            start_time = end_time - timedelta(days=7)
            date_format_mysql = '%Y-%m-%d'
            label_format_python = '%d/%m'
        elif periodo == '30d':
            start_time = end_time - timedelta(days=30)
            date_format_mysql = '%Y-%m-%d'
            label_format_python = '%d/%m'
        else:
            return jsonify({'error': 'Período inválido'}), 400

        query_result = db.session.query(
            func.date_format(SensorData.timestamp, date_format_mysql).label('period'),
            func.avg(SensorData.temperature).label('avg_temp'),
            func.avg(SensorData.humidity).label('avg_hum')
        ).filter(
            SensorData.timestamp.between(start_time, end_time)
        ).group_by(
            'period'
        ).order_by(
            'period'
        ).all()
        
        labels = [d.period for d in query_result]
        if 'h' in label_format_python or ':' in label_format_python:
            labels = [datetime.strptime(d.period, '%Y-%m-%d %H:%M' if ':' in date_format_mysql else '%Y-%m-%d %H:00').strftime(label_format_python) for d in query_result]
        else:
            labels = [datetime.strptime(d.period, '%Y-%m-%d').strftime(label_format_python) for d in query_result]

        temperatures = [round(d.avg_temp, 2) for d in query_result]
        humidities = [round(d.avg_hum, 2) for d in query_result]

    last_reading = SensorData.query.order_by(SensorData.timestamp.desc()).first()

    return jsonify({
        'labels': labels,
        'temperatures': temperatures,
        'humidities': humidities,
        'current_temp': f"{last_reading.temperature:.1f}" if last_reading else 'N/A',
        'current_hum': f"{last_reading.humidity:.1f}" if last_reading else 'N/A'
    })
@bp.route('/users')
@login_required
def list_users():
    users = User.get_all()
    return render_template('users_list.html', users=users, title="Gerenciar Usuários")

@bp.route('/user/add', methods=['GET', 'POST'])
@login_required
def add_user():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            full_name=form.full_name.data,
            email=form.email.data,
            role=form.role.data
        )
        user.set_password(form.password.data)
        user.save()
        flash('Novo usuário criado com sucesso!', 'success')
        return redirect(url_for('main.list_users'))
    return render_template('user_add.html', form=form, title="Adicionar Usuário")

@bp.route('/user/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    user = User.get_by_id(id)
    if not user:
        abort(404)
        
    form = EditUserForm(original_username=user.username, original_email=user.email)
    
    if request.method == 'GET':
        form.username.data = user.username
        form.full_name.data = user.full_name
        form.email.data = user.email
        form.role.data = user.role

    if form.validate_on_submit():
        user.username = form.username.data
        user.full_name = form.full_name.data
        user.email = form.email.data
        user.role = form.role.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('main.list_users'))

    return render_template('user_edit.html', form=form, user=user, title="Editar Usuário")

@bp.route('/user/delete/<int:id>', methods=['POST'])
@login_required
def delete_user(id):
    user_to_delete = User.get_by_id(id)
    if not user_to_delete:
        flash('Usuário não encontrado.', 'error')
        return redirect(url_for('main.list_users'))

    if user_to_delete.role == 'admin':
        flash('Não é possível remover um administrador.', 'danger')
        return redirect(url_for('main.list_users'))
    
    if user_to_delete.id == current_user.id:
        flash('Você não pode remover a si mesmo.', 'danger')
        return redirect(url_for('main.list_users'))

    user_to_delete.delete()
    flash('Usuário removido com sucesso.', 'success')
    return redirect(url_for('main.list_users'))

@bp.route('/gerenciamento', methods=['GET', 'POST'])
@login_required
def gerenciamento():
    settings = SystemSettings.get_settings()
    form = SettingsForm(obj=settings)

    if form.validate_on_submit():
        form.populate_obj(settings)
        db.session.commit()
        
        if mqtt_utils.publish_settings(settings):
            flash('Configurações salvas e publicadas com sucesso!', 'success')
        else:
            flash('Configurações salvas no banco, mas falha ao publicar no MQTT.', 'warning')
            
        return redirect(url_for('main.gerenciamento'))

    return render_template('gerenciamento.html', title="Gerenciamento", form=form)

@bp.route('/api/live_status')
@login_required
def live_status_api():
    status = get_current_status()
    return jsonify(status)

@bp.route('/bezerros')
@login_required
def list_bezerros():
    bezerros = Bezerro.get_all()
    return render_template('bezerros_list.html', bezerros=bezerros, title="Gerenciar Bezerros")

@bp.route('/bezerro/add', methods=['GET', 'POST'])
@login_required
def add_bezerro():
    form = BezerroForm()
    if form.validate_on_submit():
        novo_bezerro = Bezerro(
            nome=form.nome.data,
            sexo=form.sexo.data,
            data_nascimento=form.data_nascimento.data,
            criado_por_id=current_user.id
        )
        novo_bezerro.save()
        flash('Bezerro cadastrado com sucesso!', 'success')
        return redirect(url_for('main.list_bezerros'))
    return render_template('bezerro_add.html', form=form, title="Adicionar Bezerro")

@bp.route('/bezerro/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_bezerro(id):
    bezerro = Bezerro.get_by_id(id)
    form = BezerroForm(obj=bezerro) 
    
    if form.validate_on_submit():
        bezerro.nome = form.nome.data
        bezerro.sexo = form.sexo.data
        bezerro.data_nascimento = form.data_nascimento.data
        db.session.commit() 
        flash('Dados do bezerro atualizados com sucesso!', 'success')
        return redirect(url_for('main.list_bezerros'))

    return render_template('bezerro_edit.html', form=form, bezerro=bezerro, title="Editar Bezerro")

@bp.route('/bezerro/delete/<int:id>', methods=['POST'])
@login_required
def delete_bezerro(id):
    bezerro = Bezerro.get_by_id(id)
    if not bezerro:
        flash('Bezerro não encontrado.', 'error')
        return redirect(url_for('main.list_bezerros'))
    
    bezerro.delete()
    flash('Bezerro removido com sucesso.', 'success')
    return redirect(url_for('main.list_bezerros'))

@bp.route('/sensores/historico')
@login_required
def sensores_history():
    if current_user.role != 'admin':
        abort(403) 

    dados_completos = SensorData.query.order_by(SensorData.timestamp.desc()).all()
    
    return render_template('sensores_history.html', 
                           title="Histórico Completo", 
                           dados=dados_completos)

@bp.route('/atuadores/historico')
@login_required
def historico_atuadores():
    # Garante que apenas administradores possam acessar
    if current_user.role != 'admin':
        abort(403)

    # Busca todos os registros, ordenados do mais recente para o mais antigo
    historico = ActuatorHistory.query.order_by(ActuatorHistory.timestamp.desc()).all()
    
    return render_template('atuadores_history.html', 
                           title="Histórico de Atuadores", 
                           historico=historico)