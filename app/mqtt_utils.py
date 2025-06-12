# app/mqtt_utils.py
import paho.mqtt.client as mqtt
import time
from flask import current_app

# Vamos usar um mapa para traduzir tópicos em chaves de forma segura
TOPIC_MAP = {
    "bezerros/temperature": "temperature",
    "bezerros/umidade/status": "umidade",
    "bezerros/aquecedor/status": "heater", 
    "bezerros/vent/status": "fan",        
    "bezerros/nevoa/status": "mist",      
    "bezerros/pers/status": "pers"
}
# A lista de tópicos para se inscrever é a lista de chaves do nosso mapa
topics_to_fetch = list(TOPIC_MAP.keys())

def get_current_status():
    """
    Conecta-se ao broker, coleta as mensagens retidas e retorna um dicionário com o estado atual.
    """
    print("\n--- [DEBUG] Iniciando get_current_status ---")
    status_data = {}

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("--- [DEBUG] Conectado ao Broker com sucesso! Inscrevendo-se nos tópicos...")
            # O subscribe agora usa a lista de chaves do nosso mapa
            client.subscribe([(topic, 0) for topic in topics_to_fetch])
        else:
            print(f"--- [DEBUG] FALHA AO CONECTAR, código de retorno: {rc} ---")
            # Documentação dos códigos de erro:
            # 1: Conexão recusada - versão do protocolo incorreta
            # 2: Conexão recusada - ID de cliente inválido
            # 3: Conexão recusada - servidor indisponível
            # 4: Conexão recusada - nome de usuário ou senha incorretos
            # 5: Conexão recusada - não autorizado

    def on_message(client, userdata, msg):
        """Salva a mensagem recebida no nosso dicionário."""
        # A tradução do tópico para a chave agora é segura usando o mapa
        topic_key = TOPIC_MAP.get(msg.topic)
        if topic_key:
            decoded_payload = msg.payload.decode('utf-8')
            status_data[topic_key] = decoded_payload
            print(f"--- [DEBUG] MENSAGEM RECEBIDA: Tópico [{msg.topic}] -> Chave [{topic_key}] -> Valor [{decoded_payload}]")

    # Bloco try/except para capturar erros de conexão de rede
    try:
        # Lógica para compatibilidade de versão da biblioteca paho-mqtt
        try:
            client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
        except AttributeError:
            client = mqtt.Client()
            
        client.on_connect = on_connect
        client.on_message = on_message
        client.username_pw_set(current_app.config['MQTT_USERNAME'], current_app.config['MQTT_PASSWORD'])
        
        print("--- [DEBUG] Tentando conectar ao broker...")
        client.connect(current_app.config['MQTT_BROKER_URL'], current_app.config['MQTT_BROKER_PORT'], 60)

        client.loop_start()
        print("--- [DEBUG] Loop iniciado, aguardando 1 segundo por mensagens retidas...")
        time.sleep(1) # Aumentei o tempo para 1s para dar mais margem
        client.loop_stop()
        print("--- [DEBUG] Loop parado, desconectando.")
        client.disconnect()

    except Exception as e:
        print(f"--- [DEBUG] Ocorreu uma exceção geral ao tentar conectar/buscar dados MQTT: {e}")
        return {} # Retorna um dicionário vazio em caso de falha

    print(f"--- [DEBUG] Finalizado. Dados coletados: {status_data}")
    return status_data