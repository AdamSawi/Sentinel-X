"""Adaptateur Docker/MQTTS autour du serveur thermique du collègue."""
import json
import threading
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

import server

credentials = Path('/run/sentinel')
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='thermal-simulation')
measurement_lock = threading.Lock()
temperature = 25.0
stop = threading.Event()
last_error = None


class Temperature(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    temperature: float = Field(ge=-100, le=300)


def measure(value):
    if not client.is_connected():
        raise RuntimeError('MQTT déconnecté')
    with measurement_lock:
        result = server.receive_temperature(server.TemperatureData(temperature=value))
        payload = {
            'device_id': 'thermal-simulator',
            'message_id': str(uuid.uuid4()),
            'observed_at': datetime.now(timezone.utc).isoformat(),
            'simulated': True,
            'temperature_c': value,
        }
        publication = client.publish('sentinel/sensors/thermal-simulator/telemetry',
                                     json.dumps(payload), qos=1)
        publication.wait_for_publish(timeout=3)
        if not publication.is_published():
            raise RuntimeError('Publication MQTT non confirmée')
        return result


def run_simulation():
    global last_error
    while not stop.is_set():
        try:
            measure(temperature)
            last_error = None
        except Exception as error:
            last_error = str(error)
            print('Simulation:', last_error, flush=True)
        stop.wait(1)


@asynccontextmanager
async def lifespan(app):
    client.username_pw_set('sensors', (credentials / 'sensors.password').read_text().strip())
    client.tls_set(ca_certs=str(credentials / 'server.crt'))
    client.reconnect_delay_set(1, 10)
    client.connect_async('mqtt', 8883, 30)
    client.loop_start()
    stop.clear()
    worker = threading.Thread(target=run_simulation, daemon=True)
    worker.start()
    yield
    stop.set()
    worker.join(timeout=5)
    client.disconnect()
    client.loop_stop()


app = FastAPI(title='Sentinel-X Simulation thermique', lifespan=lifespan)


@app.get('/control')
def control():
    return FileResponse('control.html')


@app.get('/simulation')
def simulation_status():
    return {'temperature': temperature, 'mqtt_connected': client.is_connected(),
            'error': last_error}


@app.post('/simulation')
def set_temperature(data: Temperature):
    global temperature
    temperature = data.temperature
    return simulation_status()


@app.post('/temperature')
def receive_temperature(data: Temperature):
    try:
        return measure(data.temperature)
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error


app.mount('/', server.app)
