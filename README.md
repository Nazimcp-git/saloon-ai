# Salon AI Monitoring System

> Lightweight, modular AI-powered customer monitoring for salons.  
> Detects and counts customers using YOLOv8 + OpenCV. Runs on CPU.

---

## Features

- **Person Detection** — YOLOv8 nano model (fast, CPU-friendly)
- **Centroid Tracking** — Assigns temporary IDs to customers
- **Line-Crossing Counter** — Entry/exit detection with double-count prevention
- **Chair-Based Customer Detection** — Optional interactive chair zones for accurate counting
- **Automated Customer Captures** — Automatically saves customer photos when they are counted
- **Real-Time Dashboard** — Live stats + hourly traffic chart + recent captures gallery
- **Local Storage** — JSON + CSV timestamped records
- **Firebase Ready** — Optional cloud storage (toggle on/off)
- **Extension Hooks** — Gender detection, face recognition, alerts (stubs)

---

## Quick Start

### 1. Prerequisites

- Python 3.8+ installed
- Webcam (for live mode) or a video file

### 2. Setup

```bash
# Clone or copy the project
cd saloon

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (macOS/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run

```bash
# Default: webcam + dashboard
python main.py

# With a video file
python main.py --source path/to/video.mp4

# Headless mode (no video window)
python main.py --no-display

# Without dashboard
python main.py --no-dashboard

# Custom confidence threshold
python main.py --confidence 0.6 --frame-skip 5
```

### 4. Open Dashboard

Navigate to: **http://localhost:5000**

---

## Project Structure

```
saloon/
├── core/
│   ├── detection.py      # YOLOv8 person detector
│   ├── tracking.py       # Centroid-based tracker
│   └── counting.py       # Line-crossing counter
├── input/
│   └── video_stream.py   # Webcam / file / RTSP handler
├── storage/
│   ├── local_storage.py  # JSON + CSV storage
│   └── firebase_storage.py  # Optional Firebase
├── dashboard/
│   ├── app.py            # Flask server + API
│   ├── templates/        # HTML
│   └── static/           # CSS + JS
├── extensions/
│   ├── gender_detection.py   # Stub
│   ├── face_recognition.py   # Stub
│   └── alert_system.py       # Stub
├── config.py             # All settings
├── main.py               # Entry point
└── requirements.txt
```

---

## Configuration

Edit `config.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `VIDEO_SOURCE` | `0` | Webcam index, file path, or RTSP URL |
| `YOLO_MODEL` | `yolov8n.pt` | Model weights (auto-downloaded) |
| `CONFIDENCE_THRESHOLD` | `0.5` | Detection confidence (0.0–1.0) |
| `FRAME_SKIP` | `3` | Process every Nth frame |
| `RESIZE_WIDTH` | `640` | Frame resize for speed |
| `ENABLE_TRACKING`| `True` | Toggle tracking & counting logic |
| `DIRECTION_MODE` | `both` | `"entry"`, `"exit"`, or `"both"` |
| `CHAIR_DETECTION_ENABLED` | `True` | Toggle chair customer detection |
| `CHAIR_MIN_SITTING_TIME` | `180` | Min sitting time in seconds |
| `FIREBASE_ENABLED` | `False` | Toggle Firebase |
| `DEBUG_MODE` | `True` | Show video window |

---

## Keyboard Controls (Debug Mode)

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Reset counters |
| `c` | Toggle Chair Setup Mode |
| `s` | Save drawn chair zones (in Setup Mode) |
| `z` | Clear all chair zones (in Setup Mode) |

---

## Extending the System

### Adding a New Extension

1. Create a new file in `extensions/`
2. Follow the standard interface:

```python
class MyExtension:
    def __init__(self):
        self.enabled = False

    def process(self, frame, detections):
        if not self.enabled:
            return []
        # Your logic here
        return results
```

3. Import and call in `main.py`

### Multi-Camera Support

Run multiple instances with different sources:

```bash
python main.py --source 0  # Camera 1
python main.py --source 1  # Camera 2
```

### Firebase Setup

1. Create a Firebase project
2. Generate a service account key
3. Save as `serviceAccountKey.json` in project root
4. Set `FIREBASE_ENABLED = True` in config.py
5. `pip install firebase-admin`

---

## Performance Tips

- Use `yolov8n.pt` (nano) for fastest inference
- Increase `FRAME_SKIP` to 5+ on slow machines
- Reduce `RESIZE_WIDTH` to 320 for very low-end systems
- Use `--no-display` for headless server deployments

---

## Author

**Nazim**

---

## License

MIT — Free for personal and commercial use.
