import os
import re
import subprocess
import json
import threading
import time
from flask import Flask, request, send_file, abort, jsonify, Response, send_from_directory

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(BASE_DIR, "frontend", "MP3Converter", "dist")

app = Flask(
    __name__,
    static_folder=BUILD_DIR,    # where your built files live
    static_url_path=""          # mount them at the webroot
)

DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

ALLOWED_FORMATS = {"mp3", "aac", "alac", "flac", "wav", "ogg"}
ALLOWED_BITRATE = {"128", "192", "256", "320"}
FAST_FORMATS = {"mp3", "aac"}
QUALITY_FORMATS = {"alac", "flac", "wav", "ogg"}


def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()[:100]


def wipe_downloads(delay=1):
    time.sleep(delay)
    for fname in os.listdir(DOWNLOAD_DIR):
        try:
            os.remove(os.path.join(DOWNLOAD_DIR, fname))
        except OSError:
            pass


def get_video_info(youtube_url: str) -> dict:
    proc = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-warnings", youtube_url],
        capture_output=True, text=True, check=True
    )
    info = json.loads(proc.stdout)
    return {
        "title": sanitize_filename(info.get("title", "audio")),
        "duration": info.get("duration"),
        "formats": info.get("formats", [])
    }


def fast_download_ytdlp(youtube_url: str, audio_format: str, bitrate: str):
    info = get_video_info(youtube_url)
    title = info["title"]
    raw_template = os.path.join(DOWNLOAD_DIR, f"{title}.download.%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestaudio/best",
        "--extract-audio",
        "--audio-format", audio_format,
        "--no-warnings",
        "--no-playlist",
        "--force-overwrites",            # overwrite if exists
        youtube_url,
        "-o", raw_template
    ]
    if audio_format == "mp3":
        cmd += ["--audio-quality", f"{bitrate}K"]
    elif audio_format == "aac":
        cmd += ["--audio-quality", "256K"]

    subprocess.run(cmd, check=True, timeout=120)

    # locate the downloaded file
    for fn in os.listdir(DOWNLOAD_DIR):
        if fn.startswith(f"{title}.download."):
            path = os.path.join(DOWNLOAD_DIR, fn)
            final = os.path.join(DOWNLOAD_DIR, f"{title}.{audio_format}")
            if path != final:
                os.replace(path, final)
            return final, title

    raise FileNotFoundError("Fast download: file not found")


def quality_download_ffmpeg(youtube_url: str, audio_format: str, bitrate: str):
    info = get_video_info(youtube_url)
    title = info["title"]
    raw_template = os.path.join(DOWNLOAD_DIR, f"{title}.download.%(ext)s")

    # 1) Download best-quality audio
    dl_cmd = [
        "yt-dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--no-playlist",
        "--no-warnings",
        youtube_url,
        "-o", raw_template
    ]
    subprocess.run(dl_cmd, check=True, timeout=120)

    # find raw file
    raw_file = None
    for fn in os.listdir(DOWNLOAD_DIR):
        if fn.startswith(f"{title}.download."):
            raw_file = os.path.join(DOWNLOAD_DIR, fn)
            break
    if not raw_file:
        raise FileNotFoundError("Quality download: raw file not found")

    # 2) Convert with FFmpeg
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

    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", raw_file,
        "-vn"
    ]
    if audio_format == "mp3":
        cmd += ["-c:a", "libmp3lame", "-b:a",
                f"{bitrate}k", "-ar", "44100", "-ac", "2", "-q:a", "2"]
    elif audio_format == "aac":
        cmd += ["-c:a", "aac", "-b:a",
                f"{bitrate}k", "-ar", "44100", "-ac", "2", "-profile:a", "aac_low"]
    elif audio_format == "alac":
        cmd += ["-c:a", "alac", "-ar", "44100", "-ac", "2"]
    elif audio_format == "flac":
        cmd += ["-c:a", "flac", "-compression_level",
                "8", "-ar", "44100", "-ac", "2"]
    elif audio_format == "wav":
        cmd += ["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2"]
    elif audio_format == "ogg":
        cmd += ["-c:a", "libvorbis", "-b:a",
                f"{bitrate}k", "-ar", "44100", "-ac", "2"]

    cmd.append(out_file)
    subprocess.run(cmd, check=True, timeout=180)

    # cleanup raw
    os.remove(raw_file)
    return out_file, title


def streaming_download(youtube_url: str, audio_format: str, bitrate: str):
    info = get_video_info(youtube_url)
    title = info["title"]

    yt_cmd = ["yt-dlp", "-f", "bestaudio/best",
              "--no-warnings", youtube_url, "-o", "-"]
    ff_cmd = ["ffmpeg", "-hide_banner",
              "-loglevel", "error", "-i", "pipe:0", "-vn"]

    if audio_format == "mp3":
        ff_cmd += ["-c:a", "libmp3lame", "-b:a", f"{bitrate}k"]
    elif audio_format == "aac":
        ff_cmd += ["-c:a", "aac", "-b:a", f"{bitrate}k"]
    ff_cmd += ["-f", audio_format, "pipe:1"]

    yt = subprocess.Popen(yt_cmd, stdout=subprocess.PIPE)
    ff = subprocess.Popen(ff_cmd, stdin=yt.stdout, stdout=subprocess.PIPE)
    yt.stdout.close()

    def generate():
        try:
            while True:
                chunk = ff.stdout.read(16384)
                if not chunk:
                    break
                yield chunk
        finally:
            ff.terminate()
            yt.terminate()

    return generate(), title


@app.route('/search')
def search():
    q = request.args.get("query", "").strip()
    if not q:
        return abort(400, "Missing query")
    proc = subprocess.run(
        ["yt-dlp",
         "--ignore-errors",
         "--quiet",
         "--dump-json",
         "--no-playlist",
         "--flat-playlist",
         f"ytsearch8:{q}"],
        capture_output=True, text=True, check=True, timeout=15
    )
    results = []
    for line in proc.stdout.splitlines():
        try:
            info = json.loads(line)
        except:
            continue
        results.append({
            "title": info.get("title"),
            "url":   info.get("webpage_url"),
            "thumbnail": info.get("thumbnails")[0].get("url"),
            "duration":  info.get("duration")
        })
    return jsonify(results)


@app.route('/download')
def download():
    url = request.args.get("url", "").strip()
    fmt = request.args.get("format", "mp3").strip().lower()
    br = request.args.get("bitrate", "320").strip()
    method = request.args.get("method", "auto").strip().lower()

    if not url.startswith(("http://", "https://")):
        return abort(400, "Invalid URL")
    if fmt not in ALLOWED_FORMATS:
        return abort(400, "Unsupported format")
    if fmt in FAST_FORMATS and br not in ALLOWED_BITRATE:
        return abort(400, "Unsupported bitrate")

    try:
        if method == "auto":
            method = "fast" if fmt in FAST_FORMATS else "quality"

        if method == "stream" and fmt in FAST_FORMATS:
            gen, title = streaming_download(url, fmt, br)
            mime = "audio/mpeg" if fmt == "mp3" else "audio/aac"
            return Response(
                gen(),
                mimetype=mime,
                headers={
                    "Content-Disposition": f'attachment; filename="{title}.{fmt}"'}
            )
        elif method == "fast":
            file_path, title = fast_download_ytdlp(url, fmt, br)
        else:
            file_path, title = quality_download_ffmpeg(url, fmt, br)

        response = send_file(
            file_path,
            as_attachment=True,
            download_name=f"{title}.{file_path.rsplit('.', 1)[1]}",
            mimetype={
                "mp3": "audio/mpeg",
                "aac": "audio/aac",
                "alac": "audio/mp4",
                "flac": "audio/flac",
                "wav": "audio/wav",
                "ogg": "audio/ogg"
            }[fmt]
        )

        threading.Thread(target=wipe_downloads, args=(1,), daemon=True).start()
        return response

    except subprocess.CalledProcessError as e:
        app.logger.error(f"Processing error: {e}")
        return abort(500, "Processing failed")
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return abort(500, str(e))


@app.route('/formats')
def formats():
    return jsonify({
        "fast":    list(FAST_FORMATS),
        "quality": list(QUALITY_FORMATS),
        "bitrates": list(ALLOWED_BITRATE),
        "methods": ["auto", "fast", "quality", "stream"]
    })


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_spa(path):
    # 1) If requesting a real file (e.g. /favicon.ico or /assets/foo.js), serve it
    file_path = os.path.join(BUILD_DIR, path)
    if path and os.path.isfile(file_path):
        return send_from_directory(BUILD_DIR, path)

    # 2) Otherwise, always serve index.html so the client-side router can take over
    return send_from_directory(BUILD_DIR, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
