#!/usr/bin/env python3
"""
GuardRail AI — Flask Web Server
---------------------------------
Exposes the 9-layer GuardrailPipeline and the PDF scanner
as a REST API consumed by the frontend.

Endpoints:
    GET  /                          → Serves index.html
    GET  /api/health                → Health check + model status
    POST /api/analyze/text          → Analyze a text prompt
    POST /api/analyze/pdf           → Analyze an uploaded PDF
"""

import os
import sys
import time
import json
import tempfile
import traceback
import uuid

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ── Path Setup ──────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
sys.path.insert(0, BASE_DIR)

# ── App Init ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
CORS(app)

# ── Lazy-loaded pipeline (loaded once on first request) ──────────────────────
_pipeline = None
_pipeline_error = None

def get_pipeline():
    global _pipeline, _pipeline_error
    if _pipeline is not None:
        return _pipeline
    if _pipeline_error:
        return None
    try:
        from prompt_injection_detector.pipeline import GuardrailPipeline
        print("[INIT] Loading GuardrailPipeline...")
        _pipeline = GuardrailPipeline()
        print("[INIT] Pipeline ready.")
    except Exception as e:
        _pipeline_error = str(e)
        print(f"[ERROR] Pipeline failed to load: {e}")
    return _pipeline


# ── Helper: serialize a PipelineResult to dict ───────────────────────────────
def result_to_dict(res, text_preview: str = "") -> dict:
    return {
        "status": res.status,
        "verdict": res.verdict,
        "reason": res.reason,
        "layer_triggered": res.layer_triggered,
        "confidence": round(res.confidence, 4),
        "latency_ms": round(res.latency * 1000, 2),
        "text_preview": text_preview[:200] if text_preview else "",
    }


# ── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/health")
def health():
    pipeline = get_pipeline()
    return jsonify({
        "status": "ok",
        "model_loaded": pipeline is not None,
        "model_error": _pipeline_error,
        "timestamp": time.time(),
    })


@app.route("/api/analyze/text", methods=["POST"])
def analyze_text():
    pipeline = get_pipeline()
    if pipeline is None:
        return jsonify({"error": f"Pipeline not loaded: {_pipeline_error}"}), 503

    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided"}), 400

    if len(text) > 50_000:
        return jsonify({"error": "Text too long (max 50,000 characters)"}), 400

    try:
        result = pipeline.run(text=text, mock_llm_response="Safe response.")
        return jsonify({
            "mode": "text",
            "result": result_to_dict(result, text),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/analyze/pdf", methods=["POST"])
def analyze_pdf():
    pipeline = get_pipeline()
    if pipeline is None:
        return jsonify({"error": f"Pipeline not loaded: {_pipeline_error}"}), 503

    if "pdf" not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400

    pdf_file = request.files["pdf"]
    if not pdf_file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Uploaded file must be a PDF"}), 400

    # Parse scan options from form data
    chunk_size = int(request.form.get("chunk_size", 400))
    overlap = int(request.form.get("overlap", 40))
    batch_size = int(request.form.get("batch_size", 8))

    # Save to a temp file
    tmp_path = os.path.join(tempfile.gettempdir(), f"guardrail_{uuid.uuid4().hex}.pdf")
    try:
        pdf_file.save(tmp_path)

        from pdf_scanner import scan_pdf
        report = scan_pdf(
            pdf_path=tmp_path,
            chunk_size=chunk_size,
            overlap=overlap,
            batch_size=batch_size,
            verbose=False,
        )

        # Serialize report
        chunk_results = []
        for cr in report.chunk_results:
            chunk_results.append({
                "chunk_index": cr.chunk_index,
                "start_word": cr.start_word,
                "preview": cr.preview,
                "status": cr.status,
                "verdict": cr.verdict,
                "confidence": round(cr.confidence, 4),
                "reason": cr.reason,
                "layer_triggered": cr.layer_triggered,
                "latency_ms": round(cr.latency_ms, 2),
            })

        return jsonify({
            "mode": "pdf",
            "filename": pdf_file.filename,
            "page_count": report.page_count,
            "total_chunks": report.total_chunks,
            "final_verdict": report.final_verdict,
            "overall_confidence": round(report.overall_confidence, 4),
            "injection_chunks": report.injection_chunks,
            "suspicious_chunks": report.suspicious_chunks,
            "safe_chunks": report.safe_chunks,
            "scan_time_sec": round(report.scan_time_sec, 2),
            "chunk_results": chunk_results,
        })

    except ImportError as e:
        return jsonify({"error": f"Missing dependency: {e}"}), 503
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print("  GuardRail AI — Web Interface")
    print("=" * 55)
    print(f"  URL: http://127.0.0.1:5000")
    print(f"  Static: {STATIC_DIR}")
    print("=" * 55)
    # Pre-load the pipeline at startup
    get_pipeline()
    app.run(host="0.0.0.0", port=5000, debug=False)
