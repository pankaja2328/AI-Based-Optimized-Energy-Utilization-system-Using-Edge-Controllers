import paho.mqtt.client as mqtt

MQTT_BROKER = "1b68f21e37a44697a7872f3c9321ce24.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "malshan"     
MQTT_PASS = "Pankaja1"     
MQTT_TOPIC = "power/tou_domestic"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to HiveMQ broker!")
        client.subscribe(MQTT_TOPIC)
        print(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        print("Failed to connect, return code:", rc)

def on_message(client, userdata, msg):
    print(f"Received message on {msg.topic}: {msg.payload.decode()}")

client = mqtt.Client()
client.username_pw_set(MQTT_USER, MQTT_PASS)
client.tls_set()
client.on_connect = on_connect
client.on_message = on_message

print("Connecting to broker...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_forever()
