"""
Salon AI Monitoring System — Configuration
===========================================
Central configuration file. All tunable parameters live here.
Modify these values to adapt the system to your environment.
"""

import os

# ─────────────────────────────────────────────
# VIDEO SOURCE
# ─────────────────────────────────────────────
# Options:
#   0, 1, 2 ...       → Webcam index
#   "path/to/video"   → Local video file
#   "rtsp://..."      → RTSP stream (IP camera / CCTV)
VIDEO_SOURCE = 0

# ─────────────────────────────────────────────
# YOLO MODEL
# ─────────────────────────────────────────────
# Lightweight model for CPU inference.
# Options: "yolov8n.pt" (nano), "yolov8s.pt" (small)
# The model file is auto-downloaded on first run.
YOLO_MODEL = "yolov8n.pt"

# Minimum confidence to accept a detection (0.0 – 1.0)
CONFIDENCE_THRESHOLD = 0.5

# ─────────────────────────────────────────────
# PERFORMANCE
# ─────────────────────────────────────────────
# Process every Nth frame (higher = faster, less accurate)
FRAME_SKIP = 3

# Resize frame width before detection (pixels).
# Smaller = faster. Set to None to keep original size.
RESIZE_WIDTH = 640

# ─────────────────────────────────────────────
# COUNTING LINE
# ─────────────────────────────────────────────
# Horizontal line position as a fraction of frame height (0.0 = top, 1.0 = bottom)
LINE_POSITION = 0.5

# Direction that counts as "entry" or "exit":
#   "entry" → only count entries (top to bottom if "down" conceptually)
#   "exit"  → only count exits
#   "both"  → count entries (top to bottom) and exits (bottom to top)
DIRECTION_MODE = "both"

# Minimum movement (pixels) a person must cross past the line to be counted
# This creates a buffer zone around the line to prevent counting small movements
MIN_MOVEMENT_THRESHOLD = 20

# ─────────────────────────────────────────────
# TRACKING
# ─────────────────────────────────────────────
# Number of consecutive frames an object can be missing
# before it is deregistered from the tracker.
MAX_DISAPPEARED = 50

# Maximum distance (pixels) to match a detection to an
# existing tracked object. Beyond this, it's treated as new.
MAX_MATCH_DISTANCE = 80

# Whether to enable the tracking and counting system.
# If False, the system will only run object detection.
ENABLE_TRACKING = True

# ─────────────────────────────────────────────
# CHAIR DETECTION
# ─────────────────────────────────────────────
# Enable chair-based customer detection
CHAIR_DETECTION_ENABLED = True

# Minimum sitting time in seconds to count as a customer
CHAIR_MIN_SITTING_TIME = 180

# Default chair zones if no JSON config exists
# e.g., [{"id": 1, "x1": 100, "y1": 200, "x2": 300, "y2": 400}]
CHAIR_ZONES = []

# Path to the chair configuration JSON file
CHAIR_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "chair_config.json"
)

# ─────────────────────────────────────────────
# STORAGE
# ─────────────────────────────────────────────
# Directory for local data files (JSON + CSV)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# Save counts to storage every N seconds
SAVE_INTERVAL = 30

# ─────────────────────────────────────────────
# FIREBASE (OPTIONAL)
# ─────────────────────────────────────────────
# Set to True to enable Firebase Firestore storage.
# Requires firebase-admin package and a service account key.
FIREBASE_ENABLED = False

# Path to Firebase service account JSON key file
FIREBASE_KEY_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "serviceAccountKey.json"
)

# Firestore collection name for count data
FIREBASE_COLLECTION = "salon_counts"

# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────
# Flask dashboard port
DASHBOARD_PORT = 5000

# Auto-start dashboard when main.py runs
DASHBOARD_AUTOSTART = True

# ─────────────────────────────────────────────
# DEBUG / DISPLAY
# ─────────────────────────────────────────────
# Show annotated video window with bounding boxes, IDs, and counting line
DEBUG_MODE = True

# Print detection details to console
VERBOSE = False

# ─────────────────────────────────────────────
# EXTENSIONS (OPTIONAL HOOKS)
# ─────────────────────────────────────────────
# Enable optional extension modules
ENABLE_GENDER_DETECTION = False
ENABLE_FACE_RECOGNITION = False
ENABLE_ALERT_SYSTEM = False
