import os
import re
import subprocess
import json
from flask import Flask, request, send_file, abort, jsonify, Response
from flask_cors import CORS
import tempfile
import threading
import time

app = Flask(__name__)
CORS(app)
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

ALLOWED_FORMATS = {"mp3", "aac", "alac", "flac", "wav", "ogg"}
ALLOWED_BITRATE = {'128', '192', '256', '320'}

# Configuration for different approaches
FAST_FORMATS = {"mp3", "aac"}  # yt-dlp handles these well
QUALITY_FORMATS = {"alac", "flac", "wav", "ogg"}  # FFmpeg handles these better


def get_video_info(youtube_url: str) -> dict:
    """Get video info including title."""
    try:
        command = ["yt-dlp", "--dump-json", youtube_url]
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        info = json.loads(result.stdout)
        title = re.sub(r'[<>:"/\\|?*]', '', info.get('title', 'audio'))
        return {
            'title': title,
            'duration': info.get('duration'),
            'formats': info.get('formats', [])
        }
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        print(f"Error getting video info: {e}")
        raise


def fast_download_ytdlp(youtube_url: str, audio_format: str, bitrate: str) -> tuple:
    """
    Fast approach: Let yt-dlp handle everything (best for MP3, AAC)
    """
    info = get_video_info(youtube_url)
    title = info['title']
    
    with tempfile.NamedTemporaryFile(suffix=f'.{audio_format}', delete=False) as tmp_file:
        output_path = tmp_file.name
    
    try:
        command = [
            "yt-dlp",
            "-f", "bestaudio",
            "--extract-audio",
            "--audio-format", audio_format,
            youtube_url,
            "-o", output_path.replace(f'.{audio_format}', '.%(ext)s')
        ]
        
        # Quality settings for yt-dlp
        if audio_format == "mp3":
            command.extend(["--audio-quality", f"{bitrate}K"])
        elif audio_format == "aac":
            command.extend(["--audio-quality", "256K"])
            
        subprocess.run(command, check=True)
        
        # Find the actual output file
        base_path = output_path.replace(f'.{audio_format}', '')
        for ext in [audio_format, 'm4a', 'webm', 'ogg']:
            potential_file = f"{base_path}.{ext}"
            if os.path.exists(potential_file):
                return potential_file, title
                
        raise FileNotFoundError("Downloaded file not found")
        
    except subprocess.CalledProcessError as e:
        if os.path.exists(output_path):
            os.remove(output_path)
        raise e


def quality_download_ffmpeg(youtube_url: str, audio_format: str, bitrate: str) -> tuple:
    """
    Quality approach: Download best audio, then convert with FFmpeg
    (best for ALAC, FLAC, WAV, high-quality formats)
    """
    info = get_video_info(youtube_url)
    title = info['title']
    
    # Download best quality audio first
    with tempfile.NamedTemporaryFile(suffix='.m4a', delete=False) as tmp_input:
        input_path = tmp_input.name
    
    with tempfile.NamedTemporaryFile(suffix=f'.{audio_format}', delete=False) as tmp_output:
        output_path = tmp_output.name
    
    try:
        # Step 1: Download best audio quality
        download_cmd = [
            "yt-dlp",
            "-f", "bestaudio[ext=m4a]/bestaudio",
            "--no-playlist",
            youtube_url,
            "-o", input_path.replace('.m4a', '.%(ext)s')
        ]
        subprocess.run(download_cmd, check=True)
        
        # Find downloaded file
        base_path = input_path.replace('.m4a', '')
        actual_input = None
        for ext in ['m4a', 'webm', 'ogg', 'mp3']:
            potential_file = f"{base_path}.{ext}"
            if os.path.exists(potential_file):
                actual_input = potential_file
                break
                
        if not actual_input:
            raise FileNotFoundError("Downloaded file not found")
        
        # Step 2: Convert with FFmpeg for precise control
        convert_cmd = ["ffmpeg", "-y", "-i", actual_input, "-vn"]
        
        if audio_format == "mp3":
            convert_cmd.extend([
                "-c:a", "libmp3lame",
                "-b:a", f"{bitrate}k",
                "-ar", "44100",
                "-joint_stereo", "1",
                "-q:a", "0"  # Best quality
            ])
        elif audio_format == "aac":
            convert_cmd.extend([
                "-c:a", "aac",
                "-b:a", f"{bitrate}k",
                "-ar", "44100",
                "-profile:a", "aac_low"
            ])
        elif audio_format == "alac":
            convert_cmd.extend([
                "-c:a", "alac",
                "-ar", "44100"
            ])
        elif audio_format == "flac":
            convert_cmd.extend([
                "-c:a", "flac",
                "-compression_level", "8",
                "-ar", "44100"
            ])
        elif audio_format == "wav":
            convert_cmd.extend([
                "-c:a", "pcm_s16le",
                "-ar", "44100"
            ])
        elif audio_format == "ogg":
            convert_cmd.extend([
                "-c:a", "libvorbis",
                "-b:a", f"{bitrate}k",
                "-ar", "44100"
            ])
        
        convert_cmd.append(output_path)
        subprocess.run(convert_cmd, check=True)
        
        # Cleanup input file
        if os.path.exists(actual_input):
            os.remove(actual_input)
            
        return output_path, title
        
    except subprocess.CalledProcessError as e:
        # Cleanup on error
        for f in [input_path, output_path]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass
        raise e


def streaming_download(youtube_url: str, audio_format: str, bitrate: str):
    """
    Streaming approach: Start sending data immediately
    """
    info = get_video_info(youtube_url)
    title = info['title']
    
    # Use yt-dlp with ffmpeg for streaming
    command = [
        "yt-dlp",
        "-f", "bestaudio",
        youtube_url,
        "-o", "-"  # stdout
    ]
    
    ffmpeg_cmd = ["ffmpeg", "-i", "pipe:0", "-vn"]
    
    if audio_format == "mp3":
        ffmpeg_cmd.extend(["-c:a", "libmp3lame", "-b:a", f"{bitrate}k"])
    elif audio_format == "aac":
        ffmpeg_cmd.extend(["-c:a", "aac", "-b:a", f"{bitrate}k"])
    
    ffmpeg_cmd.extend(["-f", audio_format, "pipe:1"])
    
    try:
        # Chain yt-dlp | ffmpeg
        yt_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=yt_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Close yt-dlp stdout in parent to allow it to terminate
        yt_process.stdout.close()
        
        def generate():
            while True:
                data = ffmpeg_process.stdout.read(8192)
                if not data:
                    break
                yield data
            
            ffmpeg_process.wait()
            yt_process.wait()
            
        return generate(), title
        
    except Exception as e:
        print(f"Streaming error: {e}")
        raise


@app.route('/')
def home():
    return "Welcome to the Enhanced MP3 Downloader! Supports: MP3, AAC, ALAC, FLAC, WAV, OGG"


@app.route('/search', methods=['GET'])
def search():
    search_query = request.args.get('query', " ").strip()
    if not search_query:
        return abort(404, "Please provide a valid URL using the 'query' parameter.")
    
    proc = subprocess.run([
        "yt-dlp", 
        "--ignore-errors", 
        "--dump-json",
        "--no-playlist",
        f"ytsearch5:{search_query}"
    ], capture_output=True, text=True)
    
    results = []
    for line in proc.stdout.splitlines():
        try:
            info = json.loads(line)
        except json.JSONDecodeError:
            continue
        results.append({    
            "title": info.get("title"),
            "url": info.get("webpage_url"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
        })
    return jsonify(results)


@app.route('/download', methods=['GET'])
def downloads():
    video_url = request.args.get('url', " ").strip()
    bitrate = request.args.get('bitrate', '320').strip()
    audio_format = request.args.get('format', 'mp3').strip().lower()
    method = request.args.get('method', 'auto').lower()  # auto, fast, quality, stream

    # Validations
    if not video_url:
        return abort(404, "Please provide a valid URL using the 'url' parameter.")
    if bitrate not in ALLOWED_BITRATE:
        return abort(404, f"Invalid bitrate. Allowed values are: {', '.join(ALLOWED_BITRATE)}")
    if audio_format not in ALLOWED_FORMATS:
        return abort(404, f"Invalid audio format. Allowed values are: {', '.join(ALLOWED_FORMATS)}")

    try:
        # Choose method automatically if not specified
        if method == 'auto':
            if audio_format in FAST_FORMATS:
                method = 'fast'
            else:
                method = 'quality'
        
        if method == 'stream':
            # Streaming mode
            generator, title = streaming_download(video_url, audio_format, bitrate)
            
            mimetype_map = {
                'mp3': 'audio/mpeg',
                'aac': 'audio/aac',
                'alac': 'audio/mp4',
                'flac': 'audio/flac',
                'wav': 'audio/wav',
                'ogg': 'audio/ogg'
            }
            
            return Response(
                generator,
                mimetype=mimetype_map.get(audio_format, 'audio/mpeg'),
                headers={
                    "Content-Disposition": f"attachment; filename={title}.{audio_format}",
                    "Cache-Control": "no-cache"
                }
            )
            
        elif method == 'fast':
            # Fast yt-dlp method
            output_file, title = fast_download_ytdlp(video_url, audio_format, bitrate)
            
        else:  # method == 'quality'
            # Quality FFmpeg method
            output_file, title = quality_download_ffmpeg(video_url, audio_format, bitrate)
        
        def cleanup_file():
            time.sleep(30)
            try:
                if os.path.exists(output_file):
                    os.remove(output_file)
            except OSError:
                pass
        
        cleanup_thread = threading.Thread(target=cleanup_file)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        mimetype_map = {
            'mp3': 'audio/mpeg',
            'aac': 'audio/aac', 
            'alac': 'audio/mp4',
            'flac': 'audio/flac',
            'wav': 'audio/wav',
            'ogg': 'audio/ogg'
        }
        
        return send_file(
            output_file, 
            as_attachment=True, 
            download_name=f"{title}.{audio_format}",
            mimetype=mimetype_map.get(audio_format, 'audio/mpeg')
        )
        
    except subprocess.CalledProcessError as e:
        app.logger.error(f"Error processing audio: {e}")
        return abort(500, "Error processing your request")
    except Exception as e:
        app.logger.error(f"Unexpected error: {e}")
        return abort(500, "An unexpected error occurred")


@app.route('/formats', methods=['GET'])
def get_formats():
    """Return available formats and their recommended methods"""
    return jsonify({
        'formats': {
            'fast': {
                'formats': list(FAST_FORMATS),
                'description': 'Fastest processing using yt-dlp',
                'recommended_for': 'General use, quick downloads'
            },
            'quality': {
                'formats': list(QUALITY_FORMATS),
                'description': 'Highest quality using FFmpeg',
                'recommended_for': 'Audiophiles, archival purposes'
            }
        },
        'bitrates': list(ALLOWED_BITRATE),
        'methods': ['auto', 'fast', 'quality', 'stream']
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)