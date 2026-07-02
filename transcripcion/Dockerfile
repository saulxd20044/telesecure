FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Descarga el modelo de Vosk directo al contenedor
RUN wget -q https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip \
    && unzip vosk-model-small-es-0.42.zip \
    && mv vosk-model-small-es-0.42 /app/vosk-model \
    && rm vosk-model-small-es-0.42.zip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analytics_listener.py .

CMD ["python", "-u", "analytics_listener.py"]
