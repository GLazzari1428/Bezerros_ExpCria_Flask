# config.py
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'uma-chave-secreta-muito-dificil'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://db_user:abc123@localhost/bezerros_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações do Broker MQTT
    MQTT_BROKER_URL = 'oljrhome.tplinkdns.com'
    MQTT_BROKER_PORT = 1883
    MQTT_USERNAME = 'batavo'
    MQTT_PASSWORD = 'thor1428'
    MQTT_KEEPALIVE = 60