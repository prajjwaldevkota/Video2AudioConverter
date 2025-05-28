# Stage 1: build the React app
FROM node:18-alpine AS frontend
WORKDIR /app

# Install only what we need to build
COPY Frontend/MP3Converter/package*.json ./
RUN npm ci

# Build into /app/dist
COPY Frontend/MP3Converter/ ./
RUN npm run build  # outputs into /app/dist

# ────────────────────────────────────────────────────────────

# Stage 2: run Flask + bundle React
FROM python:3.11-slim

# Install ffmpeg and yt-dlp
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && curl -L \
    https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp \
    -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Python deps (make sure this file is named exactly requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn flask-cors yt-dlp

# Copy your Flask code
COPY app.py .

# Copy the React build into Flask static
RUN mkdir -p frontend/MP3Converter/dist
COPY --from=frontend /app/dist frontend/MP3Converter/dist

# Expose Cloud Run port
EXPOSE 8080

# Bind Gunicorn to the $PORT that Cloud Run provides
CMD [ "sh", "-c", \
    "exec gunicorn --bind 0.0.0.0:${PORT:-8080} app:app --workers 2" ]
