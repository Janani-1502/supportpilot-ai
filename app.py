from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from src.resolution_engine import analyze_case


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = Flask(__name__)


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/assets/<path:filename>")
def frontend_assets(filename: str):
    return send_from_directory(FRONTEND_DIR, filename)


@app.post("/analyze")
def analyze():
    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify(
            {
                "error": "Please send a JSON request body.",
            }
        ), 400

    try:
        return jsonify(analyze_case(payload))
    except (OSError, ValueError) as error:
        return jsonify(
            {
                "error": "Support data could not be loaded safely.",
                "details": str(error),
            }
        ), 500
    except Exception:
        return jsonify(
            {
                "error": "The request could not be processed safely.",
            }
        ), 500


if __name__ == "__main__":
    app.run(port=8000, debug=True)