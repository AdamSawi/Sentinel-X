FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=2
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && mkdir /data && chown 1000:1883 /data
COPY server.py integration.py control.html ./
COPY index.html ./dashboard/index.html
RUN ln -s /data/sentinel.db /app/sentinel.db
USER 1000:1883
EXPOSE 8091
CMD ["uvicorn", "integration:app", "--host", "0.0.0.0", "--port", "8091", "--no-access-log"]
