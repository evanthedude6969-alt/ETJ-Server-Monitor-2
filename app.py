from flask import Flask, render_template, jsonify
from dotenv import load_dotenv
import psutil
import platform
import socket
import time
import GPUtil
import requests
import os

load_dotenv()

app = Flask(__name__)

JELLYFIN_URL = os.getenv("JELLYFIN_URL", "http://127.0.0.1:8096").rstrip("/")
JELLYFIN_API_KEY = os.getenv("JELLYFIN_API_KEY", "")

last_network = psutil.net_io_counters()
last_network_time = time.time()


def jellyfin_headers():
    return {
        "X-Emby-Token": JELLYFIN_API_KEY
    }


def get_jellyfin():
    result = {
        "online": False,
        "name": "Jellyfin",
        "version": "Unknown",
        "active_streams": 0,
        "sessions": []
    }

    try:
        info = requests.get(
            f"{JELLYFIN_URL}/System/Info",
            headers=jellyfin_headers(),
            timeout=3
        )
        info.raise_for_status()
        info_data = info.json()

        result["online"] = True
        result["name"] = info_data.get("ServerName", "Jellyfin")
        result["version"] = info_data.get("Version", "Unknown")

        sessions_request = requests.get(
            f"{JELLYFIN_URL}/Sessions",
            headers=jellyfin_headers(),
            timeout=3
        )
        sessions_request.raise_for_status()

        for session in sessions_request.json():
            now_playing = session.get("NowPlayingItem")

            if not now_playing:
                continue

            play_state = session.get("PlayState", {})
            transcode = session.get("TranscodingInfo")
            runtime = now_playing.get("RunTimeTicks", 0)
            position = play_state.get("PositionTicks", 0)

            if transcode:
                method = "Transcoding"
            elif session.get("PlayState", {}).get("PlayMethod"):
                method = session["PlayState"]["PlayMethod"]
            else:
                method = "Direct Play"

            item_type = now_playing.get("Type", "Unknown")

            if item_type == "Episode":
                title = now_playing.get("SeriesName", "Unknown Show")
                subtitle = now_playing.get("Name", "Unknown Episode")
            else:
                title = now_playing.get("Name", "Unknown")
                subtitle = ""

            session_data = {
                "title": title,
                "subtitle": subtitle,
                "type": item_type,
                "user": session.get("UserName", "Unknown"),
                "device": session.get("DeviceName", "Unknown Device"),
                "client": session.get("Client", "Unknown Client"),
                "paused": play_state.get("IsPaused", False),
                "position": position,
                "runtime": runtime,
                "progress": round((position / runtime) * 100, 1) if runtime else 0,
                "method": method,
                "transcoding": transcode is not None
            }

            if transcode:
                session_data["transcode"] = {
                    "fps": transcode.get("Framerate", 0),
                    "completion": transcode.get("CompletionPercentage", 0),
                    "video_codec": transcode.get("VideoCodec", "Unknown"),
                    "audio_codec": transcode.get("AudioCodec", "Unknown"),
                    "width": transcode.get("Width"),
                    "height": transcode.get("Height"),
                    "hardware": transcode.get("IsVideoDirect", False) is False
                }

            result["sessions"].append(session_data)

        result["active_streams"] = len(result["sessions"])

    except Exception as error:
        result["error"] = str(error)

    return result


def get_gpu_stats():
    try:
        gpus = GPUtil.getGPUs()

        if not gpus:
            return {"available": False, "name": "GPU not detected"}

        gpu = gpus[0]

        return {
            "available": True,
            "name": gpu.name,
            "usage": round(gpu.load * 100, 1),
            "temperature": gpu.temperature,
            "memory_used": round(gpu.memoryUsed, 1),
            "memory_total": round(gpu.memoryTotal, 1),
            "memory_usage": round(gpu.memoryUtil * 100, 1)
        }

    except Exception as error:
        return {
            "available": False,
            "name": "GPU monitoring unavailable",
            "error": str(error)
        }


def get_storage():
    drives = []

    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)

            drives.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "usage": usage.percent
            })

        except (PermissionError, OSError):
            continue

    return drives


def get_network():
    global last_network, last_network_time

    current = psutil.net_io_counters()
    current_time = time.time()
    elapsed = max(current_time - last_network_time, 0.001)

    upload_speed = (
        current.bytes_sent - last_network.bytes_sent
    ) / elapsed

    download_speed = (
        current.bytes_recv - last_network.bytes_recv
    ) / elapsed

    last_network = current
    last_network_time = current_time

    return {
        "upload_speed": max(upload_speed, 0),
        "download_speed": max(download_speed, 0),
        "total_sent": current.bytes_sent,
        "total_received": current.bytes_recv
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/system")
def system_stats():
    memory = psutil.virtual_memory()
    boot_time = psutil.boot_time()
    cpu_frequency = psutil.cpu_freq()

    return jsonify({
        "cpu": {
            "usage": psutil.cpu_percent(interval=0.2),
            "per_core": psutil.cpu_percent(interval=None, percpu=True),
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "frequency": cpu_frequency.current if cpu_frequency else 0,
            "name": platform.processor()
        },
        "gpu": get_gpu_stats(),
        "ram": {
            "usage": memory.percent,
            "used": memory.used,
            "available": memory.available,
            "total": memory.total
        },
        "storage": get_storage(),
        "network": get_network(),
        "windows": {
            "hostname": socket.gethostname(),
            "os": platform.platform(),
            "uptime": int(time.time() - boot_time),
            "processes": len(psutil.pids())
        }
    })


@app.route("/api/jellyfin")
def jellyfin_stats():
    return jsonify(get_jellyfin())


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )
