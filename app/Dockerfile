FROM python:3.11-slim

# FFmpeg para pydub (MP3)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render provee $PORT; exponemos por compatibilidad
EXPOSE 10000

# Uvicorn en 0.0.0.0, puerto de entorno
ENV HOST=0.0.0.0
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
