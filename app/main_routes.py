# app/main_routes.py
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from .models import SensorData, db # Vamos precisar de SensorData e db para o log
from .mqtt_utils import get_current_status # Importa nossa nova função
from datetime import datetime
from .models import ActuatorStatus, User, SystemSettings, Bezerro
from .forms import RegistrationForm, EditUserForm, SettingsForm, BezerroForm
from flask import request, jsonify
from .mqtt_utils import publish_command
from datetime import datetime, timedelta
from sqlalchemy import func
from . import mqtt_utils

bp = Blueprint('main', __name__)

@bp.route('/')
@bp.route('/home')
@login_required
def home():
    status = get_current_status()
    
    temp_atual_str = status.get('temperature', 'N/A')
    umid_atual_str = status.get('umidade', 'N/A')

    try:
        temp_val = float(temp_atual_str)
        umid_val = float(umid_atual_str)
        
        # Cria e salva o registro no banco
        new_log = SensorData(temperature=temp_val, humidity=umid_val, timestamp=datetime.now())
        db.session.add(new_log)
        db.session.commit()
    except (ValueError, TypeError):
        print("Não foi possível salvar o log: dados de sensor inválidos ou ausentes.")

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
            date_format_mysql = '%Y-%m-%d %H:%i' # Agrupa por minuto
            label_format_python = '%H:%M'
        elif periodo == '24h':
            start_time = end_time - timedelta(days=1)
            date_format_mysql = '%Y-%m-%d %H:00' # Agrupa por hora
            label_format_python = '%d/%m %Hh'
        elif periodo == '7d':
            start_time = end_time - timedelta(days=7)
            date_format_mysql = '%Y-%m-%d' # Agrupa por dia
            label_format_python = '%d/%m'
        elif periodo == '30d':
            start_time = end_time - timedelta(days=30)
            date_format_mysql = '%Y-%m-%d' # Agrupa por dia
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
    """Lista todos os bezerros cadastrados."""
    bezerros = Bezerro.get_all()
    return render_template('bezerros_list.html', bezerros=bezerros, title="Gerenciar Bezerros")

@bp.route('/bezerro/add', methods=['GET', 'POST'])
@login_required
def add_bezerro():
    """Adiciona um novo bezerro."""
    form = BezerroForm()
    if form.validate_on_submit():
        novo_bezerro = Bezerro(
            nome=form.nome.data,
            sexo=form.sexo.data,
            data_nascimento=form.data_nascimento.data,
            criado_por_id=current_user.id  # Vincula ao usuário logado
        )
        novo_bezerro.save()
        flash('Bezerro cadastrado com sucesso!', 'success')
        return redirect(url_for('main.list_bezerros'))
    return render_template('bezerro_add.html', form=form, title="Adicionar Bezerro")

@bp.route('/bezerro/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_bezerro(id):
    bezerro = Bezerro.get_by_id(id)
    if not bezerro:
        abort(404)
    
    # apenas o criador ou um admin pode editar.
    if bezerro.criado_por_id != current_user.id and current_user.role != 'admin':
        abort(403) # Erro de "Proibido"
        
    form = BezerroForm(obj=bezerro) # `obj=bezerro` pré-popula o formulário
    
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

    # apenas o criador ou um admin pode deletar.
    if bezerro.criado_por_id != current_user.id and current_user.role != 'admin':
        flash('Você não tem permissão para remover este registro.', 'danger')
        return redirect(url_for('main.list_bezerros'))
    
    bezerro.delete()
    flash('Bezerro removido com sucesso.', 'success')
    return redirect(url_for('main.list_bezerros'))