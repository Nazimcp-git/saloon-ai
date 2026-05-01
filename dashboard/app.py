"""
Dashboard — Flask Web Server
==============================
Minimal Flask application serving the analytics dashboard
and providing REST API endpoints for real-time data.

Routes:
    GET  /           → Dashboard HTML page
    GET  /api/stats  → JSON: today's counts, hourly data
    POST /api/reset  → Reset daily counters

Usage:
    # Standalone:
    python -m dashboard.app

    # Or auto-started from main.py in a background thread
"""

import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify, request

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from storage.local_storage import LocalStorage

logger = logging.getLogger(__name__)

# ── Flask App Setup ──
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static"),
)

# Shared storage instance (set from main.py or created standalone)
_storage = None

# Shared live counts (updated from main.py pipeline)
_live_counts = {
    "entered": 0,
    "exited": 0,
    "inside": 0,
    "persons_in_frame": 0,
    "chair_count": 0,
    "total_customers": 0,
    "last_updated": None,
}


def get_storage():
    """Get or create the storage instance."""
    global _storage
    if _storage is None:
        _storage = LocalStorage()
    return _storage


def set_storage(storage_instance):
    """Set the storage instance (called from main.py)."""
    global _storage
    _storage = storage_instance


def update_live_counts(entries, exits, in_store, persons_in_frame=0, chair_count=0, total_customers=0):
    """
    Update live counts from the detection pipeline.
    Called by main.py on each processed frame.
    """
    global _live_counts
    _live_counts = {
        "entered": entries,
        "exited": exits,
        "inside": in_store,
        "persons_in_frame": persons_in_frame,
        "chair_count": chair_count,
        "total_customers": total_customers if total_customers else (entries + chair_count),
        "last_updated": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/")
def index():
    """Serve the main dashboard page."""
    return render_template("index.html")


@app.route("/api/stats")
def api_stats():
    """
    Return current statistics as JSON.

    Response:
        {
            "live": {entered, exited, inside, persons_in_frame, last_updated},
            "today_total": int,
            "hourly": {hours: [...], entered: [...], exited: [...]},
            "date": "YYYY-MM-DD",
            "system_time": "ISO timestamp"
        }
    """
    storage = get_storage()

    return jsonify({
        "live": _live_counts,
        "today_total": storage.get_total_today(),
        "hourly": storage.get_hourly_data(),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "system_time": datetime.now().isoformat(),
    })


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Reset today's counters."""
    storage = get_storage()
    storage.clear_today()

    global _live_counts
    _live_counts = {
        "entered": 0,
        "exited": 0,
        "inside": 0,
        "persons_in_frame": 0,
        "chair_count": 0,
        "total_customers": 0,
        "last_updated": datetime.now().isoformat(),
    }

    logger.info("Dashboard: counters reset via API.")
    return jsonify({"status": "ok", "message": "Counters reset."})


@app.route("/api/history")
def api_history():
    """Return all records for today."""
    storage = get_storage()
    return jsonify(storage.get_today_counts())


@app.route("/api/captures")
def api_captures():
    """Return the list of recent chair captures."""
    date_filter = request.args.get('date')
    captures_dir = os.path.join(app.static_folder, "captures")
    if not os.path.exists(captures_dir):
        return jsonify([])
        
    date_str = date_filter.replace("-", "") if date_filter else ""
    
    files = [f for f in os.listdir(captures_dir) if f.endswith(".jpg")]
    
    if date_str:
        files = [f for f in files if f"_{date_str}_" in f]
        
    files_with_time = []
    for f in files:
        full_path = os.path.join(captures_dir, f)
        files_with_time.append({
            "filename": f,
            "url": f"/static/captures/{f}",
            "time": os.path.getmtime(full_path)
        })
        
    files_with_time.sort(key=lambda x: x["time"], reverse=True)
    return jsonify(files_with_time[:12])


# ─────────────────────────────────────────────
# STANDALONE LAUNCH
# ─────────────────────────────────────────────

def start_dashboard(host="0.0.0.0", port=None, debug=False):
    """
    Start the Flask dashboard server.

    Args:
        host (str): Host to bind to.
        port (int): Port number. Defaults to config.DASHBOARD_PORT.
        debug (bool): Enable Flask debug mode.
    """
    port = port or config.DASHBOARD_PORT
    logger.info(f"Starting dashboard on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, use_reloader=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"\n  Salon AI Dashboard")
    print(f"  Open: http://localhost:{config.DASHBOARD_PORT}\n")
    start_dashboard(debug=True)
