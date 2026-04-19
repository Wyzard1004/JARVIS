FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app/base_station

COPY requirements.deploy.txt /tmp/requirements.deploy.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.deploy.txt

COPY . /app/base_station

ENV PORT=8000 \
    JARVIS_RELAY_ENABLED=false

EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
