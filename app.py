"""
Minimal HTTP API: POST raw EML bytes to /convert, get PDF back.
Query params: page (default "a4"), debug_html, unsafe (optional).
"""
import os
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
import signal
import sys
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

# Limit request body to 50 MiB (eml + attachments can be large)
MAX_CONTENT_LENGTH = 50 * 1024 * 1024
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH


@app.route("/health", methods=["GET"])
def health():
    """Liveness/readiness."""
    return jsonify({"status": "ok"})


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

        cmd = [
            "eml2pdf",
            "-n", "1",
            "-p", page,
            input_dir,
            output_dir,
        ]
        if debug_html:
            cmd.insert(1, "-d")
        if unsafe:
            cmd.append("--unsafe")

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

        pdfs = list(output_dir.glob("*.pdf"))
        if not pdfs:
            return jsonify({"error": "eml2pdf produced no PDF"}), 500

        # Single input file => single output PDF from this request; serve from memory so temp dir can be cleaned
        pdf_path = pdfs[0]
        pdf_bytes = BytesIO(pdf_path.read_bytes())
        return send_file(
            pdf_bytes,
            mimetype="application/pdf",
            as_attachment=False,
            download_name=pdf_path.name,
        )

def _handle_sigterm(signum, frame):
    sys.exit(0)

signal.signal(signal.SIGTERM, _handle_sigterm)
signal.signal(signal.SIGINT, _handle_sigterm)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
