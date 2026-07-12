from flask import Flask, render_template, jsonify
import psutil
import platform
import socket
import time

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/system")
def system_stats():
    memory = psutil.virtual_memory()
    boot_time = psutil.boot_time()

    return jsonify({
        "cpu": {
            "usage": psutil.cpu_percent(interval=0.2),
            "cores": psutil.cpu_count(logical=False),
            "threads": psutil.cpu_count(logical=True),
            "frequency": psutil.cpu_freq().current if psutil.cpu_freq() else 0
        },
        "ram": {
            "usage": memory.percent,
            "used": memory.used,
            "total": memory.total
        },
        "windows": {
            "hostname": socket.gethostname(),
            "os": platform.platform(),
            "uptime": int(time.time() - boot_time)
        }
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
