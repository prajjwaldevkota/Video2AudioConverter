# Stage 1: build the React app
FROM node:18-alpine AS frontend
WORKDIR /app
COPY Frontend/MP3Converter/package*.json ./
RUN npm ci
COPY Frontend/MP3Converter/ ./
RUN npm run build   # emits /app/dist

# Stage 2: build Flask + bundle React
FROM python:3.11-slim

# install system deps
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    nodejs \
    npm \
    && curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# install Python deps + yt-dlp + gunicorn
COPY requirement.txt .
RUN pip install --no-cache-dir -r requirement.txt yt-dlp gunicorn

# copy your Flask code (and any other modules)
COPY app.py .

# make sure the dist folder exists and copy in the React build
RUN mkdir -p frontend/MP3Converter/dist
COPY --from=frontend /app/dist frontend/MP3Converter/dist

# expose port & run
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app", "--workers", "2"]
