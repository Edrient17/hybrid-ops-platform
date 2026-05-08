from flask import Flask, jsonify, request
from datetime import datetime
import os
import time
import socket
import math
import requests

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
    if INTERNAL_OPS_API_URL == "not-configured":
        return jsonify({
            "service": SERVICE_NAME,
            "status": "not_configured",
            "message": "INTERNAL_OPS_API_URL is not configured"
        }), 503

    try:
        response = requests.get(
            f"{INTERNAL_OPS_API_URL}/ops/health",
            timeout=3,
            headers={
                "ngrok-skip-browser-warning": "true"
            }
        )

        return jsonify({
            "service": SERVICE_NAME,
            "status": "connected",
            "internal_ops_api_url": INTERNAL_OPS_API_URL,
            "internal_status_code": response.status_code,
            "internal_response": response.json()
        }), response.status_code

    except Exception as e:
        app.logger.error(f"Internal Ops API call failed: {str(e)}")
        return jsonify({
            "service": SERVICE_NAME,
            "status": "internal_api_error",
            "internal_ops_api_url": INTERNAL_OPS_API_URL,
            "error": str(e)
        }), 502


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