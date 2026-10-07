FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CUDA_VISIBLE_DEVICES=-1 \
    YOLO_CONFIG_DIR=/tmp/ultralytics

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.6.0 torchvision==0.21.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /models \
    && python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')" \
    && mv yolo11n.pt /models/yolo11n.pt \
    && python -c "import urllib.request; urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task','/models/face_landmarker.task')"

COPY service.py .
COPY static ./static
RUN useradd --uid 1000 --create-home sentinel && chown -R sentinel:sentinel /app
USER sentinel
EXPOSE 8090
CMD ["uvicorn", "service:app", "--host", "0.0.0.0", "--port", "8090", "--no-access-log"]
