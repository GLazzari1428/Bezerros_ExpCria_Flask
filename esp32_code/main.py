import _thread
import time
import machine
from machine import Pin
import network
import dht
import esp32
from umqtt.simple import MQTTClient

#WIFI_SSID = "OLJR"
#WIFI_PASS = "ajb2727ahr41941428"
WIFI_SSID = "miniac"
WIFI_PASS = "thor1428"
MQTT_BROKER = "oljrhome.tplinkdns.com"
MQTT_USER = "batavo"
MQTT_PASSWORD = "thor1428"
MQTT_CLIENT_ID = "mqtt_bezerros_user"

DHT_PIN = 4
RELE_1 = 26
RELE_2 = 25
RELE_3 = 33
SERVO = 32
SERVO_FECHADO = 40
SERVO_ABERTO = 115

CMD_AQUECEDOR = b"bezerros/heater/command"
CMD_VENTILADOR = b"bezerros/fan/command"
CMD_NEVOA = b"bezerros/mist/command"
CMD_PERSIANA = b"bezerros/pers/command"
TOPICO_CONF_TEMP_FRIO = b"sistema/config/temp_frio"
TOPICO_CONF_TEMP_QUENTE = b"sistema/config/temp_quente"
TOPICO_PUB_TEMP = b"bezerros/temperature"
TOPICO_PUB_PERSIANA = b"bezerros/pers/status"
TOPICO_PUB_AQUECEDOR = b"bezerros/aquecedor/status"
TOPICO_PUB_VENTILADOR = b"bezerros/vent/status"
TOPICO_PUB_NEVOA = b"bezerros/nevoa/status"
TOPICO_PUB_UMIDADE = b"bezerros/umidade/status"

aquecedor = machine.Pin(RELE_1, machine.Pin.OUT, value=0)
ventilador = machine.Pin(RELE_2, machine.Pin.OUT, value=1) 
nevoa = machine.Pin(RELE_3, machine.Pin.OUT, value=1)
sensor = dht.DHT11(Pin(4, Pin.IN, Pin.PULL_UP)) #Pin.PULL_UP faz o DHT11 funcionar (resistor pullup interno)
servo = machine.PWM(machine.Pin(SERVO), freq=50)
servo.duty(SERVO_FECHADO)

controles = {'persiana_aberta': False}
limites = {
    'temp_frio': 15.0,
    'temp_quente': 25.0,
    'temp_muito_quente': 30.0
}
controles_manuais = {
    'aquecedor': False,
    'ventilador': False,
    'nevoa': False,
    'persiana': False
}
cliente = None
last_known_temp = 0.0
last_known_hum = 0.0

def conectar_wifi():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Conectando WiFi...')
        sta_if.active(True)
        sta_if.connect(WIFI_SSID, WIFI_PASS)
        while not sta_if.isconnected():
            time.sleep(0.5)
    print('WiFi Conectado:', sta_if.ifconfig())

def sub_callback(topic, msg):
    global limites, controles_manuais
    print(f"Comando recebido: {topic.decode()} | {msg.decode()}")
    
    if topic in [CMD_AQUECEDOR, CMD_VENTILADOR, CMD_NEVOA, CMD_PERSIANA]:
        print("MODO MANUAL ATIVADO.")
        if topic == CMD_AQUECEDOR:
            aquecedor.value(1 if msg == b"1" else 0)
            controles_manuais['aquecedor'] = True
        elif topic == CMD_VENTILADOR:
            ventilador.value(0 if msg == b"1" else 1)
            controles_manuais['ventilador'] = True
        elif topic == CMD_NEVOA:
            nevoa.value(0 if msg == b"1" else 1)
            controles_manuais['nevoa'] = True
        elif topic == CMD_PERSIANA:
            servo.duty(SERVO_ABERTO if msg == b"1" else SERVO_FECHADO)
            controles['persiana_aberta'] = (msg == b"1")
            controles_manuais['persiana'] = True
    
    elif topic == TOPICO_CONF_TEMP_FRIO:
        limites['temp_frio'] = float(msg)
        print(f"Novo limite 'temp_frio' definido para: {limites['temp_frio']}")
    elif topic == TOPICO_CONF_TEMP_QUENTE:
        limites['temp_quente'] = float(msg)
        limites['temp_muito_quente'] = float(msg) + 5.0
        print(f"Novos limites 'temp_quente'({limites['temp_quente']}) e 'muito_quente'({limites['temp_muito_quente']}) definidos.")

def thread_mqtt():
    global cliente
    cliente = MQTTClient(
        MQTT_CLIENT_ID, MQTT_BROKER,
        user=MQTT_USER, password=MQTT_PASSWORD, keepalive=60
    )
    cliente.set_callback(sub_callback)
    cliente.connect()
    
    print("Inscrevendo-se nos tópicos...")
    cliente.subscribe(CMD_AQUECEDOR)
    cliente.subscribe(CMD_VENTILADOR)
    cliente.subscribe(CMD_NEVOA)
    cliente.subscribe(CMD_PERSIANA)
    cliente.subscribe(TOPICO_CONF_TEMP_FRIO)
    cliente.subscribe(TOPICO_CONF_TEMP_QUENTE)
    print(f"MQTT Conectado e inscrito nos tópicos em {MQTT_BROKER}")

    while True:
        try:
            cliente.check_msg()
        except Exception as e:
            print(f"Erro MQTT: {e}")
        time.sleep(0.1)

def thread_controle():
    global cliente, controles_manuais, last_known_temp, last_known_hum
    
    try:
        sensor.measure()
        last_known_temp = sensor.temperature()
        last_known_hum = sensor.humidity()
    except Exception as e:
        print("Falha na leitura inicial do sensor. Usando valores padrão.")

    while True:
        print("--------------------")
        
        try:
            sensor.measure()
            temp_atual = sensor.temperature()
            umid_atual = sensor.humidity()
            #temp_atual = 20 
            #umid_atual = 50
            print(f"Leitura: Temp={temp_atual}°C, Umid={umid_atual}%")
        except Exception as e:
            print(f"Falha ao ler o sensor: {e}. Pulando este ciclo.")
            time.sleep(5)
            continue

        if temp_atual != last_known_temp or umid_atual != last_known_hum:
            if any(controles_manuais.values()):
                print(f"!!! Mudança de sensor detectada (T:{last_known_temp}->{temp_atual}, U:{last_known_hum}->{umid_atual}). Resetando para modo automático. !!!")
                controles_manuais['aquecedor'] = False
                controles_manuais['ventilador'] = False
                controles_manuais['nevoa'] = False
                controles_manuais['persiana'] = False
        
        last_known_temp = temp_atual
        last_known_hum = umid_atual

        if any(controles_manuais.values()):
            print(f"MODO MANUAL ATIVO. (Será resetado na próxima mudança de sensor)")
        else:
            print("MODO AUTOMÁTICO ATIVO.")

        estado_atual = ""
        if temp_atual < limites['temp_frio']:
            estado_atual = "FRIO"
        elif temp_atual >= limites['temp_muito_quente']:
            estado_atual = "MUITO_QUENTE"
        elif temp_atual >= limites['temp_quente']:
            estado_atual = "QUENTE"
        else:
            estado_atual = "NORMAL"
        print(f"Estado Térmico Atual: {estado_atual}")

        if not controles_manuais['aquecedor']:
            aquecedor.value(1 if estado_atual == "FRIO" else 0)
        
        if not controles_manuais['ventilador']:
            ventilador.value(0 if estado_atual in ["QUENTE", "MUITO_QUENTE"] else 1)

        if not controles_manuais['nevoa']:
            nevoa.value(0 if estado_atual == "MUITO_QUENTE" else 1)
        
        if not controles_manuais['persiana']:
            if estado_atual in ["QUENTE", "MUITO_QUENTE"] and not controles['persiana_aberta']:
                servo.duty(SERVO_ABERTO)
                controles['persiana_aberta'] = True
            elif estado_atual in ["FRIO", "NORMAL"] and controles['persiana_aberta']:
                servo.duty(SERVO_FECHADO)
                controles['persiana_aberta'] = False
        
        try:
            
            status_ventilador = b"1" if ventilador.value() == 0 else b"0"
            status_nevoa = b"1" if nevoa.value() == 0 else b"0"
            status_persiana = b"1" if controles['persiana_aberta'] else b"0"
            
            cliente.publish(TOPICO_PUB_TEMP, str(temp_atual).encode(), retain=True)
            cliente.publish(TOPICO_PUB_PERSIANA, status_persiana, retain=True)
            cliente.publish(TOPICO_PUB_UMIDADE, str(umid_atual).encode(), retain=True)
            cliente.publish(TOPICO_PUB_AQUECEDOR, str(aquecedor.value()).encode(), retain=True)
            cliente.publish(TOPICO_PUB_VENTILADOR, status_ventilador, retain=True)
            cliente.publish(TOPICO_PUB_NEVOA, status_nevoa, retain=True)
        except Exception as e:
            print(f"Erro ao publicar status MQTT: {e}")

        time.sleep(5)

conectar_wifi()
_thread.start_new_thread(thread_mqtt, ())
_thread.start_new_thread(thread_controle, ())
while True:
    time.sleep(1)
