# app/mqtt_utils.py
import paho.mqtt.client as mqtt
import time
from flask import current_app

def get_client():

    client = mqtt.Client()

    if current_app.config.get('MQTT_USERNAME'):
        client.username_pw_set(
            current_app.config['MQTT_USERNAME'],
            current_app.config.get('MQTT_PASSWORD')
        )
    return client


def get_current_status():
    print("\n--- [DEBUG] Iniciando get_current_status ---")
    status_data = {}
    
    topics_to_fetch = {
        "bezerros/temperature": "temperature",
        "bezerros/umidade/status": "umidade",
        "bezerros/aquecedor/status": "heater",
        "bezerros/vent/status": "fan",
        "bezerros/nevoa/status": "mist",
        "bezerros/pers/status": "pers"
    }

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("--- [DEBUG] Conectado ao Broker com sucesso! Inscrevendo-se nos tópicos...")
            client.subscribe([(topic, 0) for topic in topics_to_fetch.keys()])
        else:
            print(f"--- [DEBUG] FALHA AO CONECTAR, código de retorno: {rc} ---")

    def on_message(client, userdata, msg):
        topic_key = topics_to_fetch.get(msg.topic)
        if topic_key:
            decoded_payload = msg.payload.decode('utf-8')
            status_data[topic_key] = decoded_payload
            print(f"--- [DEBUG] MENSAGEM RECEBIDA: Tópico [{msg.topic}] -> Chave [{topic_key}] -> Valor [{decoded_payload}]")

    try:
        client = get_client() 
        client.on_connect = on_connect
        client.on_message = on_message
        
        print("--- [DEBUG] Tentando conectar ao broker...")
        client.connect(
            current_app.config['MQTT_BROKER_URL'],
            current_app.config['MQTT_BROKER_PORT'],
            current_app.config.get('MQTT_KEEPALIVE', 60)
        )

        client.loop_start()
        print("--- [DEBUG] Loop iniciado, aguardando 1 segundo por mensagens retidas...")
        time.sleep(1) 
        client.loop_stop()
        print("--- [DEBUG] Loop parado, desconectando.")
        client.disconnect()

    except Exception as e:
        print(f"--- [DEBUG] Ocorreu uma exceção geral ao tentar conectar/buscar dados MQTT: {e}")
        return {}

    print(f"--- [DEBUG] Finalizado. Dados coletados: {status_data}")
    return status_data


def publish_command(topic, payload, retain=False):
    try:
        client = get_client()
        client.connect(
            current_app.config['MQTT_BROKER_URL'],
            current_app.config['MQTT_BROKER_PORT'],
            current_app.config.get('MQTT_KEEPALIVE', 60)
        )
        client.loop_start()
        time.sleep(0.2)
        
        result = client.publish(topic, payload, retain=retain)
        
        client.loop_stop()
        client.disconnect()
        return result.rc == mqtt.MQTT_ERR_SUCCESS
    except Exception as e:
        print(f"ERRO ao publicar comando MQTT: {e}")
        return False


def publish_settings(settings):
    try:
        client = get_client()
        client.connect(
            current_app.config['MQTT_BROKER_URL'],
            current_app.config['MQTT_BROKER_PORT'],
            current_app.config.get('MQTT_KEEPALIVE', 60)
        )
        client.loop_start()
        
        client.publish('sistema/config/temp_frio', str(settings.temp_frio), retain=True)
        client.publish('sistema/config/temp_quente', str(settings.temp_quente), retain=True)
        client.publish('sistema/config/umidade_baixa', str(settings.umidade_baixa), retain=True)
        client.publish('sistema/config/umidade_alta', str(settings.umidade_alta), retain=True)
        
        client.loop_stop()
        client.disconnect()
        print("Configurações publicadas no MQTT com sucesso.")
        return True
    except Exception as e:
        print(f"Erro ao publicar configurações no MQTT: {e}")
        return False