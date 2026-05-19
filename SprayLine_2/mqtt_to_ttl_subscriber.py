"""
MQTT -> RDF observation TTL -> RDF-native SPARQL inference.

Install:
    pip install rdflib paho-mqtt

Run broker, then:
    python mqtt_to_ttl_subscriber.py

Expected MQTT topic:
    sprayline/+/window
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
import paho.mqtt.client as mqtt
from rdflib import Graph, Namespace, Literal, RDF
from rdflib.namespace import XSD

BASE_DIR = Path(__file__).resolve().parent
OBS_TTL = BASE_DIR / 'SprayLine_runtime_observation.ttl'
MIS = Namespace('http://nkust.edu.tw/mislab#')
STH = Namespace('http://nkust.edu.tw/mislab/cnc/ontology/sth#')

BROKER_HOST = '127.0.0.1'
BROKER_PORT = 1883
TOPIC = 'sprayline/+/window'


def json_to_observation_ttl(payload: dict) -> None:
    window_id = payload['window_id']
    w = STH[f'Window_{window_id}']
    g = Graph()
    g.bind('mis', MIS)
    g.bind('sth', STH)
    g.add((w, RDF.type, STH.SensingWindow))
    g.add((w, MIS.hasWindowId, Literal(window_id)))
    g.add((w, MIS.inFlow, Literal(payload['filter']['in_flow'], datatype=XSD.decimal)))
    g.add((w, MIS.outFlow, Literal(payload['filter']['out_flow'], datatype=XSD.decimal)))
    g.add((w, MIS.sprayWidth, Literal(payload['nozzle']['spray_width'], datatype=XSD.decimal)))
    g.add((w, MIS.targetSprayWidth, Literal(payload['target']['spray_width'], datatype=XSD.decimal)))
    g.add((w, MIS.sprayPressure, Literal(payload['nozzle']['spray_pressure'], datatype=XSD.decimal)))
    g.add((w, MIS.targetSprayPressure, Literal(payload['target']['spray_pressure'], datatype=XSD.decimal)))
    g.add((w, MIS.measuredThickness, Literal(payload['quality']['measured_thickness'], datatype=XSD.decimal)))
    g.add((w, MIS.targetThickness, Literal(payload['target']['thickness'], datatype=XSD.decimal)))
    ts = payload.get('timestamp', datetime.now(timezone.utc).isoformat())
    g.add((w, MIS.observedAt, Literal(ts, datatype=XSD.dateTime)))
    g.serialize(destination=OBS_TTL, format='turtle')


def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f'Connected: {reason_code}')
    client.subscribe(TOPIC)
    print(f'Subscribed: {TOPIC}')


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        json_to_observation_ttl(payload)
        print(f'Wrote observation TTL from {msg.topic}: {OBS_TTL}')
        # Optional: run RDF-native inference immediately after each MQTT message.
        from rdf_native_infer_sparql import run_inference
        run_inference()
    except Exception as exc:
        print(f'ERROR processing MQTT message: {exc}')


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
    client.loop_forever()


if __name__ == '__main__':
    main()
