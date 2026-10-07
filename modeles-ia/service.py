"""Service vision conteneurisé : navigateur -> YOLO/MediaPipe -> Grafana/API."""
import asyncio
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import cv2
import mediapipe as mp
import numpy as np
from fastapi import FastAPI, HTTPException, Request as FastAPIRequest
from fastapi.responses import FileResponse, Response
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from ultralytics import YOLO


MODELS = Path('/models')
CREDS = Path('/run/sentinel')
MAX_IMAGE_BYTES = 2_000_000
lock = threading.Lock()
last_event = 0.0

person_model = YOLO(str(MODELS / 'yolo11n.pt'))
face_model = vision.FaceLandmarker.create_from_options(
    vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=str(MODELS / 'face_landmarker.task')),
        running_mode=vision.RunningMode.IMAGE,
        num_faces=1,
        min_face_detection_confidence=0.3,
        min_face_presence_confidence=0.3,
    )
)

app = FastAPI(title='Sentinel-X Vision')


def report_event(persons, faces, confidence, processing_ms):
    global last_event
    now = time.monotonic()
    if persons == 0 or now - last_event < 1:
        return
    last_event = now
    payload = {
        'device_id': 'browser-camera-01',
        'message_id': str(uuid.uuid4()),
        'observed_at': datetime.now(timezone.utc).isoformat(),
        'simulated': False,
        'event_type': 'presence',
        'zone': 'camera-principale',
        'confidence': confidence,
        'description': f'personnes={persons}; visages={faces}',
        'model': 'combined',
        'detections': persons,
        'processing_ms': processing_ms,
    }
    token = (CREDS / 'vision.password').read_text().strip()
    request = Request(
        'http://backend:8000/api/events',
        data=json.dumps(payload).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        urlopen(request, timeout=2).close()
    except OSError:
        pass


def analyze(jpeg):
    started = time.perf_counter()
    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError('Image JPEG invalide')
    result = person_model.predict(frame, classes=[0], conf=0.25, imgsz=640,
                                  device='cpu', verbose=False)[0]
    persons = 0
    faces = 0
    best_confidence = 0.0
    height, width = frame.shape[:2]
    for box in result.boxes:
        x1, y1, x2, y2 = [int(value) for value in box.xyxy[0].tolist()]
        confidence = float(box.conf[0])
        persons += 1
        best_confidence = max(best_confidence, confidence)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 190, 255), 2)
        cv2.putText(frame, f'personne {confidence:.2f}', (x1, max(22, y1 - 7)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 190, 255), 2)
        head_y2 = min(height, y1 + max(1, int((y2 - y1) * 0.4)))
        crop = frame[max(0, y1):head_y2, max(0, x1):min(width, x2)]
        if crop.size == 0:
            continue
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        detection = face_model.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
        if detection.face_landmarks:
            faces += 1
            for landmark in detection.face_landmarks[0][::20]:
                point = (x1 + int(landmark.x * crop.shape[1]), y1 + int(landmark.y * crop.shape[0]))
                cv2.circle(frame, point, 1, (0, 255, 80), -1)
    processing_ms = (time.perf_counter() - started) * 1000
    cv2.putText(frame, f'YOLO + visage | {persons} personne(s) | {faces} visage(s) | {processing_ms:.0f} ms',
                (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 80), 2)
    report_event(persons, faces, best_confidence, processing_ms)
    ok, encoded = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise ValueError('Encodage impossible')
    return encoded.tobytes()


@app.get('/')
def index():
    return FileResponse('static/index.html')


@app.get('/health')
def health():
    return {'status': 'ok', 'model': 'yolo11n+mediapipe', 'camera': 'browser'}


@app.post('/analyze')
async def analyze_frame(request: FastAPIRequest):
    content = await request.body()
    if not content or len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(413, 'Image absente ou trop volumineuse')
    try:
        with lock:
            output = await asyncio.to_thread(analyze, content)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return Response(output, media_type='image/jpeg', headers={'Cache-Control': 'no-store'})
