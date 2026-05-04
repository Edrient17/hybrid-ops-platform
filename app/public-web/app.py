from flask import Flask, jsonify, request
from datetime import datetime
import os
import time
import socket
import math

app = Flask(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "public-web-app")
APP_VERSION = os.getenv("APP_VERSION", "v0.1.0")
INTERNAL_OPS_API_URL = os.getenv("INTERNAL_OPS_API_URL", "not-configured")


@app.route("/")
def index():
    return jsonify({
        "service": SERVICE_NAME,
        "message": "Public Web App running on AWS ECS",
        "version": APP_VERSION,
        "hostname": socket.gethostname(),
        "endpoints": [
            "/health",
            "/version",
            "/status/internal",
            "/error",
            "/slow",
            "/stress"
        ]
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": SERVICE_NAME,
        "version": APP_VERSION,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route("/version")
def version():
    return jsonify({
        "service": SERVICE_NAME,
        "version": APP_VERSION
    })


@app.route("/status/internal")
def status_internal():
    return jsonify({
        "service": SERVICE_NAME,
        "internal_ops_api_url": INTERNAL_OPS_API_URL,
        "message": "Internal Ops API integration placeholder",
        "status": "not_connected_yet"
    })


@app.route("/error")
def error():
    app.logger.error("Intentional error triggered from /error endpoint")
    return jsonify({
        "status": "error",
        "message": "Intentional error for CloudWatch alarm test"
    }), 500


@app.route("/slow")
def slow():
    delay = int(request.args.get("delay", 5))
    app.logger.warning(f"Slow endpoint triggered. delay={delay}s")
    time.sleep(delay)
    return jsonify({
        "status": "ok",
        "message": f"Response delayed by {delay} seconds"
    })


@app.route("/stress")
def stress():
    app.logger.warning("CPU stress endpoint triggered")
    result = 0
    for i in range(1, 500000):
        result += math.sqrt(i)

    return jsonify({
        "status": "ok",
        "message": "CPU stress test completed",
        "result": result
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)