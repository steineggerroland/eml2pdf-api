"""
Minimal HTTP API: POST raw EML bytes to /convert, get PDF back.
Query params: page (default "a4"), debug_html, unsafe (optional).
"""
import time
import os
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
import signal
import sys
from flask import Flask, request, send_file, jsonify
import json

app = Flask(__name__)

# Limit request body to 50 MiB (eml + attachments can be large)
MAX_CONTENT_LENGTH = 50 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

@app.route("/health", methods=["GET"])
def health():
    """Liveness/readiness."""
    return jsonify({"status": "healthy"})


@app.route("/convert", methods=["POST"])
def convert():
    """
    Convert EML to PDF.
    Body: raw EML file bytes.
    Query params:
      page: page size, e.g. "a4", "a4 landscape", "letter" (default: "a4")
      debug_html: "1" or "true" to keep intermediate HTML
      unsafe: "1" or "true" to skip HTML sanitization
    """
    raw = request.get_data()
    if not raw:
        return jsonify({"error": "Missing body: send raw EML bytes"}), 400

    page = request.args.get("page", "a4").strip()
    debug_html = request.args.get("debug_html", "").lower() in ("1", "true", "yes")
    unsafe = request.args.get("unsafe", "").lower() in ("1", "true", "yes")

    with tempfile.TemporaryDirectory() as tmp:
        input_dir = Path(tmp) / "in"
        output_dir = Path(tmp) / "out"
        input_dir.mkdir()
        output_dir.mkdir()

        eml_path = input_dir / "message.eml"
        eml_path.write_bytes(raw)
        # eml2pdf 2.x requires a subcommand (convert_dir or convert_file); the old
        # flat CLI (eml2pdf -n 1 in out) made "1" look like a subcommand name.
        pdf_out = output_dir / "mail.pdf"

        cmd = ["eml2pdf", "convert_file"]
        if debug_html:
            cmd.append("-d")
        if unsafe:
            cmd.append("--unsafe")
        cmd.extend(["-p", page, str(eml_path), str(pdf_out)])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            return jsonify({
                "error": "eml2pdf failed",
                "stderr": result.stderr or result.stdout,
            }), 500

        if not pdf_out.is_file():
            return jsonify({"error": "eml2pdf produced no PDF"}), 500

        pdf_bytes = BytesIO(pdf_out.read_bytes())
        return send_file(
            pdf_bytes,
            mimetype="application/pdf",
            as_attachment=False,
            download_name="mail.pdf",
        )

@app.before_request
def start_timer():
    request.start_time = time.time()

@app.after_request
def log_request(response):
    elapsed = time.time() - request.start_time
    elapsed_ms = elapsed * 1000
    app.logger.info(
        f"Request: {request.method} {request.path} | "
        f"Status: {response.status_code} | "
        f"Time: {elapsed_ms:.2f}ms"
    )
 
    return response

@app.teardown_request
def log_exception(exception):
    if exception:  # Only log if an exception occurred
        elapsed = time.time() - request.start_time
        elapsed_ms = elapsed * 1000
        app.logger.info(
            f"Request failed: {request.method} {request.path} | "
            f"Exception: {str(exception)} | "
            f"Time: {elapsed_ms:.2f}ms"
        )
        app.logger.info(json.dumps(dict(request.headers)))


def _handle_sigterm(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(debug=True,host="0.0.0.0", port=port)
