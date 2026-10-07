"""Run inside backend: validates live ingestion and storage, not AI models."""
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import paho.mqtt.client as mqtt

BASE = 'http://backend:8000'
CREDS = Path('/run/sentinel')


def request(path, payload=None, role=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if role:
        headers['Authorization'] = 'Bearer ' + (CREDS / f'{role}.password').read_text().strip()
    if token:
        headers['Authorization'] = token
    req = Request(BASE + path, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    with urlopen(req, timeout=5) as response:
        return json.load(response)


def expect_status(status, *args, **kwargs):
    try:
        request(*args, **kwargs)
    except HTTPError as error:
        assert error.code == status, error.code
    else:
        raise AssertionError(f'Expected HTTP {status}')


def wait_for(predicate):
    for _ in range(50):
        if predicate():
            return
        time.sleep(.2)
    raise AssertionError('Expected observation not received')


health = request('/api/health')
assert health['database'] == 'ok'
wait_for(lambda: request('/api/health')['mqtt'] == 'connected')
stamp = datetime.now(timezone.utc).isoformat()
event = dict(device_id='smoke-vision', message_id=str(uuid.uuid4()), observed_at=stamp,
             simulated=True, event_type='intrusion', zone='test', confidence=.92,
             model='combined', detections=2, processing_ms=42.5)
expect_status(401, '/api/events', event, token='Bearer invalid')
expect_status(401, '/api/events', event, role='sensors')
expect_status(422, '/api/events', {**event, 'confidence': 2}, role='vision')
assert request('/api/events', event, role='vision')['inserted'] is True
assert request('/api/events', event, role='vision')['inserted'] is False
assert any(x['message_id'] == event['message_id'] for x in request('/api/events'))
anomaly = {**event, 'message_id': str(uuid.uuid4()), 'event_type': 'anomaly', 'description': 'Integration test only'}
assert request('/api/events', anomaly, role='vision')['inserted'] is True

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='sentinel-smoke-' + uuid.uuid4().hex[:8])
client.username_pw_set('sensors', (CREDS / 'sensors.password').read_text().strip())
client.tls_set(ca_certs=str(CREDS / 'server.crt'))
client.connect('mqtt', 8883, 30)
client.loop_start()
wait_for(client.is_connected)
sample = dict(device_id='smoke-sensor', message_id=str(uuid.uuid4()), observed_at=stamp,
              simulated=True, temperature_c=27.5, humidity_pct=40, gas_index=20)
client.publish('sentinel/sensors/smoke-sensor/telemetry', json.dumps(sample), qos=1).wait_for_publish(5)
wait_for(lambda: any(x['message_id'] == sample['message_id'] for x in request('/api/telemetry')))
before = request('/api/health')['rejected_since_start']
client.publish('sentinel/sensors/smoke-sensor/telemetry', '{invalid', qos=1).wait_for_publish(5)
wait_for(lambda: request('/api/health')['rejected_since_start'] > before)
forbidden = {**event, 'message_id': str(uuid.uuid4())}
client.publish('sentinel/vision/smoke-vision/events', json.dumps(forbidden), qos=1).wait_for_publish(5)
time.sleep(1)
assert not any(x['message_id'] == forbidden['message_id'] for x in request('/api/events'))
client.disconnect()
client.loop_stop()
with urlopen(BASE + '/metrics', timeout=5) as response:
    assert b'sentinel_observations_total' in response.read()
print('PASS: API, PostgreSQL, MQTT TLS, producer permissions, validation, metrics and duplicate handling.')
print('Test observations are marked simulated (smoke-sensor / smoke-vision).')
