# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, FloatField, DateField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Optional
from .models import User

class LoginForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    remember_me = BooleanField('Lembrar-me')
    submit = SubmitField('Entrar')

class RegistrationForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    full_name = StringField('Nome Completo', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Senha', validators=[DataRequired()])
    password2 = PasswordField(
        'Repita a Senha', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Função', choices=[('publico_geral', 'Público Geral'), ('admin', 'Administrador')], default='publico_geral', validators=[DataRequired()])
    submit = SubmitField('Registrar')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Este nome de usuário já está em uso.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Este email já está em uso.')


class EditUserForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired()])
    full_name = StringField('Nome Completo', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    role = SelectField('Função', choices=[('publico_geral', 'Público Geral'), ('admin', 'Administrador')], validators=[DataRequired()])
    password = PasswordField('Nova Senha (deixe em branco para não alterar)')
    password2 = PasswordField(
        'Repita a Nova Senha', validators=[EqualTo('password')])
    submit = SubmitField('Salvar Alterações')

    def __init__(self, original_username, original_email, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('Este nome de usuário já está em uso.')

    def validate_email(self, email):
        if email.data != self.original_email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('Este email já está em uso.')


class SettingsForm(FlaskForm):
    temp_frio = FloatField('Temperatura Mínima Ideal (°C)', validators=[DataRequired()], 
                           description="Abaixo deste valor, o ambiente é considerado 'Frio'.")
    temp_quente = FloatField('Temperatura Máxima Ideal (°C)', validators=[DataRequired()],
                             description="Acima deste valor, o ambiente é considerado 'Quente'.")
    umidade_baixa = FloatField('Umidade Mínima Ideal (%)', validators=[DataRequired()],
                               description="Abaixo deste valor, o ambiente é considerado 'Seco'.")
    umidade_alta = FloatField('Umidade Máxima Ideal (%)', validators=[DataRequired()],
                              description="Acima deste valor, o ambiente é considerado 'Úmido'.")
    submit = SubmitField('Salvar Configurações')

class BezerroForm(FlaskForm):
    nome = StringField('Nome do Bezerro', validators=[DataRequired()])
    sexo = SelectField('Sexo', choices=[('Macho', 'Macho'), ('Fêmea', 'Fêmea')], validators=[DataRequired()])
    data_nascimento = DateField('Data de Nascimento', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Salvar')