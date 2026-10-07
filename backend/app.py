"""Local integration API. Models are supplied by the team's producers."""
import json
import logging
import secrets
import shutil
import sqlite3
import tempfile
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

import paho.mqtt.client as mqtt
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

log = logging.getLogger('sentinel')
CREDS = Path('/run/sentinel')
LEGACY_DB = Path('/legacy/sentinel.sqlite3')
lock = threading.Lock()
connected = threading.Event()
rejections = 0
rates = defaultdict(deque)
accepted_metric = Counter('sentinel_observations', 'New observations accepted since process start', ['kind'])
event_metric = Counter('sentinel_events', 'New events accepted since process start', ['event_type'])
vision_detection_metric = Counter(
    'sentinel_vision_detections', 'Objects detected by vision producers', ['model', 'event_type'])
vision_confidence_metric = Gauge(
    'sentinel_vision_confidence', 'Confidence of the latest vision event', ['model', 'device'])
vision_inference_metric = Histogram(
    'sentinel_vision_inference_seconds', 'Vision inference duration reported by producers', ['model'])
reject_metric = Counter('sentinel_rejections', 'Rejected inputs since process start', ['reason', 'transport'])
http_metric = Counter('sentinel_http_requests', 'API requests since process start', ['route', 'status'])
duration_metric = Histogram('sentinel_http_duration_seconds', 'API request duration', ['route'])
mqtt_metric = Gauge('sentinel_mqtt_connected', 'Backend subscribed to MQTT')
db_metric = Gauge('sentinel_database_up', 'PostgreSQL connectivity checked during scrape')
for kind in ('event', 'telemetry'):
    accepted_metric.labels(kind)
for kind in ('intrusion', 'presence', 'heartbeat', 'anomaly'):
    event_metric.labels(kind)


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
    event_type: Literal['intrusion', 'presence', 'heartbeat', 'anomaly']
    zone: str = Field(min_length=1, max_length=64)
    confidence: float | None = Field(default=None, ge=0, le=1)
    description: str = Field(default='', max_length=256)
    model: Literal['yolo', 'face', 'combined'] | None = None
    detections: int | None = Field(default=None, ge=0, le=1000)
    processing_ms: float | None = Field(default=None, ge=0, le=60000)


def connect_db():
    return psycopg.connect(host='postgres', dbname='sentinel', user='sentinel_app',
                           password=(CREDS / 'app-db.password').read_text().strip(),
                           connect_timeout=2, row_factory=dict_row)


def reject(reason='invalid_message', transport='mqtt'):
    global rejections
    with lock:
        rejections += 1
    reject_metric.labels(reason, transport).inc()
    try:
        with connect_db() as db:
            db.execute('INSERT INTO security_events(received_at,reason,transport) VALUES(%s,%s,%s)',
                       (time.time(), reason, transport))
    except psycopg.Error:
        log.warning('Could not persist security event')


def save(kind, observation):
    now = time.time()
    payload = observation.model_dump(mode='json')
    with connect_db() as db:
        cursor = db.execute(
            'INSERT INTO observations(kind, device, message_id, received_at, payload) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(kind,device,message_id) DO NOTHING',
            (kind, observation.device_id, observation.message_id, now, Jsonb(payload)),
        )
        inserted = cursor.rowcount == 1
    if inserted:
        accepted_metric.labels(kind).inc()
        if kind == 'event':
            event_metric.labels(observation.event_type).inc()
            if observation.model:
                count = observation.detections if observation.detections is not None else 1
                vision_detection_metric.labels(observation.model, observation.event_type).inc(count)
                if observation.confidence is not None:
                    vision_confidence_metric.labels(observation.model, observation.device_id).set(observation.confidence)
                if observation.processing_ms is not None:
                    vision_inference_metric.labels(observation.model).observe(observation.processing_ms / 1000)
    return inserted


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
    except psycopg.Error:
        reject('storage_error', 'mqtt')
        log.exception('MQTT storage failed')


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id='sentinel-backend')
client.on_connect = on_connect
client.on_subscribe = on_subscribe
client.on_disconnect = on_disconnect
client.on_message = on_message


@asynccontextmanager
async def lifespan(app):
    with connect_db() as db:
        db.execute('SELECT 1 FROM observations LIMIT 1')
        # Preserve legacy observations; duplicates are ignored on later starts.
        if LEGACY_DB.exists():
            # SQLite may need writable shared-memory files to read a WAL database.
            # Read a private copy, including its WAL, without altering the archive.
            with tempfile.TemporaryDirectory() as directory:
                copy = Path(directory) / LEGACY_DB.name
                shutil.copyfile(LEGACY_DB, copy)
                wal = Path(str(LEGACY_DB) + '-wal')
                if wal.exists():
                    shutil.copyfile(wal, str(copy) + '-wal')
                legacy = sqlite3.connect(copy)
                try:
                    for kind, device, mid, received, payload in legacy.execute(
                        'SELECT kind,device,message_id,received_at,payload FROM observations'):
                        db.execute('INSERT INTO observations(kind,device,message_id,received_at,payload) VALUES(%s,%s,%s,%s,%s) ON CONFLICT(kind,device,message_id) DO NOTHING',
                                   (kind, device, mid, received, Jsonb(json.loads(payload))))
                finally:
                    legacy.close()
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
            reject('authentication', 'http')
            raise HTTPException(401, 'Invalid producer token')
        try:
            rate_limit('http:' + role)
        except HTTPException:
            reject('rate_limit', 'http')
            raise
    return check


@app.middleware('http')
async def limit_body(request: Request, call_next):
    started = time.perf_counter()
    if request.method == 'POST':
        size = 0
        chunks = []
        async for chunk in request.stream():
            size += len(chunk)
            if size > 16384:
                from fastapi.responses import JSONResponse
                reject('payload_size', 'http')
                return JSONResponse({'detail': 'Payload too large'}, status_code=413)
            chunks.append(chunk)
        request._body = b''.join(chunks)
    response = await call_next(request)
    if response.status_code == 422:
        reject('validation', 'http')
    if request.url.path != '/metrics':
        route = request.url.path if request.url.path in ('/api/health', '/api/events', '/api/telemetry') else 'other'
        http_metric.labels(route, str(response.status_code)).inc()
        duration_metric.labels(route).observe(time.perf_counter() - started)
    return response


@app.get('/metrics', include_in_schema=False)
def metrics():
    mqtt_metric.set(1 if connected.is_set() else 0)
    try:
        with connect_db() as db:
            db.execute('SELECT 1')
        db_metric.set(1)
    except psycopg.Error:
        db_metric.set(0)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get('/api/health')
def health():
    with connect_db() as db:
        db.execute('SELECT 1')
    return {'api': 'ok', 'database': 'ok', 'mqtt': 'connected' if connected.is_set() else 'disconnected',
            'rejected_since_start': rejections, 'server_time': datetime.now(timezone.utc).isoformat()}


def rows(kind, limit):
    with connect_db() as db:
        data = db.execute('SELECT * FROM observations WHERE kind=%s ORDER BY id DESC LIMIT %s', (kind, limit)).fetchall()
    return [{**row['payload'], 'received_at': row['received_at'], 'id': row['id']} for row in data]


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
