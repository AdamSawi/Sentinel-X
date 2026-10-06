"""Local integration API. Models are supplied by the team's producers."""
import json
import logging
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

import paho.mqtt.client as mqtt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

log = logging.getLogger('sentinel')
CREDS = Path('/run/sentinel')
DB = '/data/sentinel.sqlite3'
lock = threading.Lock()
connected = threading.Event()
rejections = 0
rates = defaultdict(deque)


class Observation(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    device_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    message_id: str = Field(min_length=1, max_length=96)
    observed_at: datetime
    simulated: bool

    @field_validator('observed_at')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError('An explicit timezone is required')
        return value


class Telemetry(Observation):
    temperature_c: float = Field(ge=-100, le=300)
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    gas_index: float | None = Field(default=None, ge=0, le=1000)
    presence: bool | None = None


class Intrusion(Observation):
    event_type: Literal['intrusion', 'presence', 'heartbeat']
    zone: str = Field(min_length=1, max_length=64)
    confidence: float | None = Field(default=None, ge=0, le=1)
    description: str = Field(default='', max_length=256)


def connect_db():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def reject():
    global rejections
    with lock:
        rejections += 1


def save(kind, observation):
    now = time.time()
    payload = observation.model_dump(mode='json')
    with connect_db() as db:
        cursor = db.execute(
            'INSERT OR IGNORE INTO observations(kind, device, message_id, received_at, payload) VALUES(?,?,?,?,?)',
            (kind, observation.device_id, observation.message_id, now, json.dumps(payload)),
        )
        return cursor.rowcount == 1


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        client.subscribe([('sentinel/sensors/+/telemetry', 1), ('sentinel/vision/+/events', 1)])
    else:
        connected.clear()


def on_subscribe(client, userdata, mid, reason_codes, properties):
    if all(not code.is_failure for code in reason_codes):
        connected.set()


def on_disconnect(client, userdata, flags, reason_code, properties):
    connected.clear()


def on_message(client, userdata, message):
    try:
        if len(message.payload) > 16384:
            raise ValueError('Payload too large')
        parts = message.topic.split('/')
        kind = 'telemetry' if parts[1] == 'sensors' else 'event'
        model = Telemetry if kind == 'telemetry' else Intrusion
        observation = model.model_validate_json(message.payload)
        if observation.device_id != parts[2]:
            raise ValueError('Device/topic mismatch')
        # Bound work per stream, even when the payload claims many device IDs.
        rate_limit('mqtt:' + kind, maximum=120)
        save(kind, observation)
    except (ValueError, ValidationError, HTTPException):
        reject()
        log.warning('MQTT observation rejected')
    except sqlite3.Error:
        reject()
        log.exception('MQTT storage failed')


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='sentinel-backend')
client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_disconnect = on_disconnect
client.on_message = on_message


@asynccontextmanager
async def lifespan(app):
    with connect_db() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('''CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY, kind TEXT NOT NULL, device TEXT NOT NULL,
            message_id TEXT NOT NULL, received_at REAL NOT NULL, payload TEXT NOT NULL,
            UNIQUE(kind, device, message_id))''')
        db.execute('CREATE INDEX IF NOT EXISTS observations_kind_id ON observations(kind,id)')
    client.username_pw_set('backend', (CREDS / 'backend.password').read_text().strip())
    client.tls_set(ca_certs=str(CREDS / 'server.crt'))
    client.reconnect_delay_set(1, 10)
    client.connect_async('mqtt', 8883, 30)
    client.loop_start()
    yield
    client.disconnect()
    client.loop_stop()


app = FastAPI(title='Sentinel-X Integration API', lifespan=lifespan)


def rate_limit(key, maximum=120):
    now = time.monotonic()
    with lock:
        window = rates[key]
        while window and window[0] < now - 60:
            window.popleft()
        if len(window) >= maximum:
            raise HTTPException(429, 'Rate limit exceeded')
        window.append(now)


def authorized(role):
    def check(authorization: Annotated[str | None, Header()] = None):
        expected = 'Bearer ' + (CREDS / f'{role}.password').read_text().strip()
        if not authorization or not secrets.compare_digest(authorization, expected):
            reject()
            raise HTTPException(401, 'Invalid producer token')
        rate_limit('http:' + role)
    return check


@app.middleware('http')
async def limit_body(request: Request, call_next):
    if request.method == 'POST':
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 16384:
                from fastapi.responses import JSONResponse
                reject()
                return JSONResponse({'detail': 'Payload too large'}, status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    response = await call_next(request)
    if response.status_code == 422:
        reject()
    return response


@app.get('/api/health')
def health():
    with connect_db() as db:
        db.execute('SELECT 1')
    return {'api': 'ok', 'database': 'ok', 'mqtt': 'connected' if connected.is_set() else 'disconnected',
            'rejected_since_start': rejections, 'server_time': datetime.now(timezone.utc).isoformat()}


def rows(kind, limit):
    with connect_db() as db:
        data = db.execute('SELECT * FROM observations WHERE kind=? ORDER BY id DESC LIMIT ?', (kind, limit)).fetchall()
    return [{**json.loads(row['payload']), 'received_at': row['received_at'], 'id': row['id']} for row in data]


@app.get('/api/telemetry')
def telemetry(limit: int = Query(default=200, ge=1, le=1000)):
    return rows('telemetry', limit)


@app.get('/api/events')
def events(limit: int = Query(default=100, ge=1, le=1000)):
    return rows('event', limit)


@app.post('/api/telemetry', dependencies=[Depends(authorized('sensors'))])
def post_telemetry(observation: Telemetry):
    return {'accepted': True, 'inserted': save('telemetry', observation)}


@app.post('/api/events', dependencies=[Depends(authorized('vision'))])
def post_event(observation: Intrusion):
    return {'accepted': True, 'inserted': save('event', observation)}
