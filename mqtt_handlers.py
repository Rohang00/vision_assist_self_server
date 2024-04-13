import json
import time

import paho.mqtt.client as mqtt

mqtt_broker = '10.42.0.1'
mqtt_port = 1883

client = mqtt.Client('vision_assist')

def on_connect(client, userdata, flags, rc):
   print(f'Connected @ {time.time()}')

def on_disconnect(client, userdata, rc):
   print(f'Disconnected @ {time.time()}')


client.on_connect = on_connect
client.on_disconnect = on_disconnect


if __name__ == 'main':
   client.connect(mqtt_broker, mqtt_port, 60)
   client.publish('detections', json.dumps({'key' : 'value'}))
   print('published')
