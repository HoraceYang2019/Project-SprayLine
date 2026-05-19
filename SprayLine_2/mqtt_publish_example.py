import json
import paho.mqtt.client as mqtt

payload = {
    'window_id': 'w0413004',
    'timestamp': '2026-04-26T09:00:00+08:00',
    'filter': {'in_flow': 100.0, 'out_flow': 72.0},
    'nozzle': {'spray_width': 82.0, 'spray_pressure': 2.4},
    'quality': {'measured_thickness': 55.0},
    'target': {'spray_width': 80.0, 'spray_pressure': 2.5, 'thickness': 50.0}
}

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect('127.0.0.1', 1883, 60)
client.publish('sprayline/lineA/window', json.dumps(payload), qos=1)
client.disconnect()
print(json.dumps(payload, indent=2))
