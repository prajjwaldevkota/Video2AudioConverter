import os
import re
import subprocess
import json
import threading
import time
from flask import Flask, request, send_file, abort, jsonify, Response, after_this_request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


def wipe_downloads(delay=1):
    """Wait `delay` seconds, then remove all files in DOWNLOAD_DIR."""
    time.sleep(delay)
    for fname in os.listdir(DOWNLOAD_DIR):
        path = os.path.join(DOWNLOAD_DIR, fname)
        try:
            os.remove(path)
        except OSError:
            pass


DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ALLOWED_FORMATS = {"mp3", "aac", "alac", "flac", "wav", "ogg"}
ALLOWED_BITRATE = {"128", "192", "256", "320"}

FAST_FORMATS = {"mp3", "aac"}
QUALITY_FORMATS = {"alac", "flac", "wav", "ogg"}


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()


def get_video_info(youtube_url: str) -> dict:
    proc = subprocess.run(
        ["yt-dlp", "--dump-json", youtube_url],
        capture_output=True, text=True, check=True
    )
    info = json.loads(proc.stdout)
    title = sanitize_filename(info.get("title", "audio"))
    return {
        "title": title,
        "duration": info.get("duration"),
        "formats": info.get("formats", [])
    }


def fast_download_ytdlp(youtube_url: str, audio_format: str, bitrate: str) -> tuple:
    info = get_video_info(youtube_url)
    title = info["title"]
    # template with .download marker
    raw_template = os.path.join(DOWNLOAD_DIR, f"{title}.download.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestaudio",
        "--extract-audio",
        "--audio-format", audio_format,
        youtube_url,
        "-o", raw_template
    ]
    if audio_format == "mp3":
        cmd += ["--audio-quality", f"{bitrate}K"]
    elif audio_format == "aac":
        cmd += ["--audio-quality", "256K"]
    subprocess.run(cmd, check=True)

    # find the actual downloaded file
    for fn in os.listdir(DOWNLOAD_DIR):
        if fn.startswith(f"{title}.download."):
            return os.path.join(DOWNLOAD_DIR, fn), title

    raise FileNotFoundError("Fast download: file not found")


def quality_download_ffmpeg(youtube_url: str, audio_format: str, bitrate: str) -> tuple:
    info = get_video_info(youtube_url)
    title = info["title"]
    # raw download marker
    raw_template = os.path.join(DOWNLOAD_DIR, f"{title}.download.%(ext)s")

    # Step 1: download best-quality audio as m4a
    dl_cmd = [
        "yt-dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--no-playlist",
        youtube_url,
        "-o", raw_template
    ]
    subprocess.run(dl_cmd, check=True)

    # find raw file
    raw_file = None
    for fn in os.listdir(DOWNLOAD_DIR):
        if fn.startswith(f"{title}.download."):
            raw_file = os.path.join(DOWNLOAD_DIR, fn)
            break
    if not raw_file:
        raise FileNotFoundError("Quality download: raw file not found")

    # Step 2: convert with FFmpeg
    # determine final extension
    ext_map = {
        "mp3":  "mp3",
        "aac":  "m4a",
        "alac": "m4a",
        "flac": "flac",
        "wav":  "wav",
        "ogg":  "ogg"
    }
    final_ext = ext_map[audio_format]
    out_file = os.path.join(DOWNLOAD_DIR, f"{title}.{final_ext}")

    cmd = ["ffmpeg", "-y", "-i", raw_file, "-vn", "-preset", "ultrafast",]
    if audio_format == "mp3":
        cmd += [
            "-c:a", "libmp3lame",
            "-b:a", f"{bitrate}k",
            "-ar", "44100",
            "-joint_stereo", "1"
        ]
    elif audio_format == "aac":
        cmd += [
            "-c:a", "aac",
            "-b:a", f"{bitrate}k",
            "-ar", "44100",
            "-profile:a", "aac_low"
        ]
    elif audio_format == "alac":
        cmd += ["-c:a", "alac", "-ar", "44100"]
    elif audio_format == "flac":
        cmd += ["-c:a", "flac", "-compression_level", "8", "-ar", "44100"]
    elif audio_format == "wav":
        cmd += ["-c:a", "pcm_s16le", "-ar", "44100"]
    elif audio_format == "ogg":
        cmd += ["-c:a", "libvorbis", "-b:a", f"{bitrate}k", "-ar", "44100"]

    cmd.append(out_file)
    subprocess.run(cmd, check=True)

    # remove the raw file immediately
    os.remove(raw_file)
    return out_file, title


def streaming_download(youtube_url: str, audio_format: str, bitrate: str):
    info = get_video_info(youtube_url)
    title = info["title"]

    yt_cmd = ["yt-dlp", "-f", "bestaudio", youtube_url, "-o", "-"]
    ff_cmd = ["ffmpeg", "-i", "pipe:0", "-vn"]
    if audio_format == "mp3":
        ff_cmd += ["-c:a", "libmp3lame", "-b:a", f"{bitrate}k"]
    elif audio_format == "aac":
        ff_cmd += ["-c:a", "aac", "-b:a", f"{bitrate}k"]
    ff_cmd += ["-f", audio_format, "pipe:1"]

    yt = subprocess.Popen(yt_cmd, stdout=subprocess.PIPE)
    ff = subprocess.Popen(ff_cmd, stdin=yt.stdout, stdout=subprocess.PIPE)
    yt.stdout.close()

    def generate():
        for chunk in iter(lambda: ff.stdout.read(8192), b""):
            yield chunk
        ff.wait()
        yt.wait()

    return generate(), title


@app.route('/search')
def search():
    q = request.args.get("query", "").strip()
    if not q:
        return abort(400, "Missing query")
    proc = subprocess.run(
        ["yt-dlp",
            "--ignore-errors",
            "--dump-json",
            "--no-playlist",
            "--flat-playlist",
            f"ytsearch5:{q}"],
        capture_output=True, text=True, check=True
    )
    out = []
    for line in proc.stdout.splitlines():
        try:
            info = json.loads(line)
        except:
            continue
        out.append({
            "title": info.get("title"),
            "url":   info.get("webpage_url"),
            "thumbnail": info.get("thumbnail"),
            "duration":  info.get("duration")
        })
    return jsonify(out)


@app.route('/download')
def download():
    url = request.args.get("url", "").strip()
    fmt = request.args.get("format", "mp3").strip().lower()
    br = request.args.get("bitrate", "320").strip()
    method = request.args.get("method", "auto").strip().lower()

    if not url.startswith("http"):
        return abort(400, "Invalid URL")
    if fmt not in ALLOWED_FORMATS:
        return abort(400, "Unsupported format")
    if fmt == "mp3" and br not in ALLOWED_BITRATE:
        return abort(400, "Unsupported bitrate")

    try:
        # pick method
        if method == "auto":
            method = "fast" if fmt in FAST_FORMATS else "quality"

        if method == "stream":
            gen, title = streaming_download(url, fmt, br)
            mime = {
                "mp3": "audio/mpeg",
                "aac": "audio/aac"
            }.get(fmt, "application/octet-stream")
            return Response(
                gen(),
                mimetype=mime,
                headers={
                    "Content-Disposition": f"attachment; filename={title}.{fmt}"}
            )

        elif method == "fast":
            file_path, title = fast_download_ytdlp(url, fmt, br)

        else:  # quality
            file_path, title = quality_download_ffmpeg(url, fmt, br)

        mime_map = {
            "mp3": "audio/mpeg",
            "aac": "audio/aac",
            "alac": "audio/mp4",
            "flac": "audio/flac",
            "wav": "audio/wav",
            "ogg": "audio/ogg"
        }

        response = send_file(
            file_path,
            as_attachment=True,
            download_name=f"{title}.{file_path.split('.')[-1]}",
            mimetype=mime_map.get(fmt, "application/octet-stream")
        )

        t = threading.Thread(target=wipe_downloads, args=(1,), daemon=True)
        t.start()

        return response

    except subprocess.CalledProcessError as e:
        app.logger.error(f"Error: {e}")
        return abort(500, "Processing error")
    except Exception as e:
        app.logger.error(f"Unexpected: {e}")
        return abort(500, "Unexpected error")


@app.route('/formats')
def formats():
    return jsonify({
        "fast":    list(FAST_FORMATS),
        "quality": list(QUALITY_FORMATS),
        "bitrates": list(ALLOWED_BITRATE),
        "methods": ["auto", "fast", "quality", "stream"]
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
