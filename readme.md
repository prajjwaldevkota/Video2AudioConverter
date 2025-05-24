# SoundScape Audio Downloader API

A lightweight Flask-based service that lets you search YouTube and download video audio in a variety of formats (MP3, AAC, ALAC, FLAC, WAV, OGG). Under the hood it uses `yt-dlp` for fetching and (optionally) FFmpeg for high-quality conversion. Everything runs in a local `downloads/` folder (auto-cleaned after each request), and it’s fully containerized with Docker.

---

## 🚀 Features

- **Search** YouTube for up to 5 videos via `/search?query=<keywords>`.
- **Download** video audio in:
  - Fast mode (pure `yt-dlp`) for MP3/AAC  
  - Quality mode (`yt-dlp` + FFmpeg) for ALAC/FLAC/WAV/OGG  
  - Streaming mode (yt-dlp → FFmpeg pipe)  
- Supports formats: `mp3`, `aac`, `alac`, `flac`, `wav`, `ogg`.
- Configurable MP3 bitrate: `128`, `192`, `256`, `320` kbps.
- Automatic cleanup of `downloads/` folder after each response.
- CORS-enabled for easy integration with any frontend.

---

## 📋 Prerequisites

- **Docker** (for containerized deployment)  
  _or_  
- **Python 3.8+**, `pip`, `ffmpeg`, `yt-dlp` installed on your host machine

---

## ⚙️ Installation

### 1. Clone this repo
```bash
git clone https://github.com/yourusername/soundscape-backend.git
cd soundscape-backend

# create & activate a virtual environment
python3 -m venv venv
source venv/bin/activate    # Linux/Mac
.\venv\Scripts\activate     # Windows PowerShell

# install Python deps
pip install --no-cache-dir -r requirements.txt
pip install --no-cache-dir yt-dlp

# install ffmpeg via your package manager, e.g.:
sudo apt update && sudo apt install ffmpeg

# start the server
python app.py
