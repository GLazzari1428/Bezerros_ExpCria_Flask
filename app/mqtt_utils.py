# app/mqtt_utils.py
import paho.mqtt.client as mqtt
import time
from flask import current_app

# --- NOVA FUNÇÃO AUXILIAR ---
def get_client():
    """
    Cria, configura e retorna uma instância do cliente MQTT.
    Esta função centraliza a lógica de criação do cliente.
    """
    try:
        # Tenta usar a API de Callback v1, se disponível (paho-mqtt >= 2.0)
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        # Fallback para versões mais antigas
        client = mqtt.Client()

    # Define o usuário e senha apenas se eles forem fornecidos no config.py
    if current_app.config.get('MQTT_USERNAME'):
        client.username_pw_set(
            current_app.config['MQTT_USERNAME'],
            current_app.config.get('MQTT_PASSWORD')
        )
    return client

# --- FUNÇÕES EXISTENTES, AGORA USANDO get_client() ---

def get_current_status():
    """
    Conecta-se ao broker, coleta as mensagens retidas e retorna um dicionário com o estado atual.
    """
    print("\n--- [DEBUG] Iniciando get_current_status ---")
    status_data = {}
    
    # Lista de tópicos para se inscrever
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
        client = get_client() # Usa a nova função auxiliar
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
    """Conecta, publica um único comando e desconecta."""
    try:
        client = get_client() # Usa a nova função auxiliar
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
    """
    Publica todas as configurações do sistema para o broker MQTT com retenção.
    """
    try:
        client = get_client() # Usa a nova função auxiliar
        client.connect(
            current_app.config['MQTT_BROKER_URL'],
            current_app.config['MQTT_BROKER_PORT'],
            current_app.config.get('MQTT_KEEPALIVE', 60)
        )
        client.loop_start()
        
        # Publica cada configuração com a flag de retenção (retain=True)
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