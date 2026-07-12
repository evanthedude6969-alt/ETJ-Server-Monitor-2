from flask import Flask, render_template, jsonify
import psutil
import platform
import socket
import time
import GPUtil

app = Flask(__name__)

last_network = psutil.net_io_counters()
last_network_time = time.time()


def get_gpu_stats():
    try:
        gpus = GPUtil.getGPUs()

        if not gpus:
            return {
                "available": False,
                "name": "GPU not detected"
            }

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
    global last_network
    global last_network_time

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


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
        threaded=True
    )
