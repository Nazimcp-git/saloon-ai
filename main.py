"""
Salon AI Monitoring System — Main Entry Point
================================================
Orchestrates the full detection → tracking → counting pipeline.

Usage:
    python main.py                    # Run with webcam (default)
    python main.py --source video.mp4 # Run with video file
    python main.py --no-dashboard     # Run without web dashboard
    python main.py --no-display       # Run headless (no video window)

Pipeline:
    1. Initialize all modules from config
    2. Optionally start Flask dashboard in background thread
    3. Main loop: read → detect → track → count → save → display
    4. Cleanup on exit
"""

import os
import sys
import time
import logging
import argparse
import threading
import signal
from datetime import datetime

import cv2
import numpy as np

import config
from core.detection import PersonDetector
from core.tracking import CentroidTracker
from core.counting import LineCrossingCounter
from core.chair_detection import ChairDetector
from input.video_stream import VideoStream
from storage.local_storage import LocalStorage

# ── Logging Setup ──
logging.basicConfig(
    level=logging.DEBUG if config.VERBOSE else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("salon_ai")

# ── Globals for Chair Setup Mode ──
chair_setup_mode = False
drawing_start = None
current_box = None

def mouse_callback(event, x, y, flags, param):
    global chair_setup_mode, drawing_start, current_box
    if not chair_setup_mode:
        return
    
    chair_detector = param
    if event == cv2.EVENT_LBUTTONDOWN:
        drawing_start = (x, y)
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing_start is not None:
            current_box = (drawing_start[0], drawing_start[1], x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        if drawing_start is not None:
            chair_detector.add_zone(drawing_start[0], drawing_start[1], x, y)
            drawing_start = None
            current_box = None


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Salon AI Monitoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source", type=str, default=None,
        help="Video source: file path, webcam index (0,1..), or RTSP URL"
    )
    parser.add_argument(
        "--no-dashboard", action="store_true",
        help="Disable the web dashboard"
    )
    parser.add_argument(
        "--no-display", action="store_true",
        help="Disable the video display window (headless mode)"
    )
    parser.add_argument(
        "--confidence", type=float, default=None,
        help=f"Detection confidence threshold (default: {config.CONFIDENCE_THRESHOLD})"
    )
    parser.add_argument(
        "--frame-skip", type=int, default=None,
        help=f"Process every Nth frame (default: {config.FRAME_SKIP})"
    )
    return parser.parse_args()


def start_dashboard_thread(storage):
    """Start the Flask dashboard in a background daemon thread."""
    from dashboard.app import start_dashboard, set_storage
    set_storage(storage)

    thread = threading.Thread(
        target=start_dashboard,
        kwargs={"host": "0.0.0.0", "port": config.DASHBOARD_PORT},
        daemon=True,
        name="dashboard-thread",
    )
    thread.start()
    logger.info(
        f"Dashboard started: http://localhost:{config.DASHBOARD_PORT}"
    )
    return thread


def draw_overlay(frame, tracked_objects, bboxes, counter, detector_info):
    """
    Draw bounding boxes, IDs, counting line, and stats on the frame.

    Args:
        frame: BGR image to draw on (modified in-place).
        tracked_objects: {id: (cx, cy)} from tracker.
        bboxes: {id: (x1, y1, x2, y2)} from tracker.
        counter: LineCrossingCounter instance.
        detector_info: dict with model info.
        chair_detector: Optional ChairDetector instance.

    Returns:
        frame with overlay drawn.
    """
    h, w = frame.shape[:2]
    line_y = counter.get_line_y()
    counts = counter.get_counts()

    # ── Draw counting line ──
    cv2.line(frame, (0, line_y), (w, line_y), (0, 255, 255), 2)
    cv2.putText(
        frame, "COUNTING LINE", (10, line_y - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1
    )

    # ── Draw direction arrow ──
    arrow_x = w - 60
    if config.DIRECTION_MODE in ["entry", "both"]:
        cv2.arrowedLine(
            frame, (arrow_x, line_y - 30), (arrow_x, line_y + 30),
            (0, 255, 0), 2, tipLength=0.3
        )
        cv2.putText(
            frame, "ENTRY", (arrow_x - 25, line_y + 50),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1
        )
    if config.DIRECTION_MODE in ["exit", "both"]:
        arrow_x_exit = arrow_x - 60 if config.DIRECTION_MODE == "both" else arrow_x
        cv2.arrowedLine(
            frame, (arrow_x_exit, line_y + 30), (arrow_x_exit, line_y - 30),
            (0, 0, 255), 2, tipLength=0.3
        )
        cv2.putText(
            frame, "EXIT", (arrow_x_exit - 20, line_y - 40),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1
        )

    # ── Draw bounding boxes and IDs ──
    for obj_id, (cx, cy) in tracked_objects.items():
        bbox = bboxes.get(obj_id)
        if bbox:
            x1, y1, x2, y2 = [int(v) for v in bbox]

            # Box color: green if below line, blue if above
            color = (0, 200, 0) if cy > line_y else (200, 120, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            # ID label
            label = f"ID:{obj_id}"
            label_size = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )[0]
            cv2.rectangle(
                frame,
                (x1, y1 - label_size[1] - 8),
                (x1 + label_size[0] + 4, y1),
                color, -1
            )
            cv2.putText(
                frame, label, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
            )

        # Centroid dot
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

    # ── Stats overlay (top-left) ──
    overlay_h = 100
    overlay = frame[0:overlay_h, 0:260].copy()
    cv2.rectangle(frame, (0, 0), (260, overlay_h), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.3, frame[0:overlay_h, 0:260], 0.7, 0,
                    frame[0:overlay_h, 0:260])

    y_text = 25
    cv2.putText(
        frame, f"Entered: {counts['entered']}", (10, y_text),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2
    )
    y_text += 25
    cv2.putText(
        frame, f"Exited:  {counts['exited']}", (10, y_text),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2
    )
    y_text += 25
    cv2.putText(
        frame, f"Inside:  {counts['inside']}", (10, y_text),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2
    )

    # ── Draw Chair Zones ──
    global chair_setup_mode, current_box
    if config.CHAIR_DETECTION_ENABLED and 'chair_detector' in globals() and chair_detector:
        for zone in chair_detector.get_zones():
            zid = zone["id"]
            x1, y1, x2, y2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]
            state = chair_detector.get_states().get(zid, {})
            
            # Color coding
            if state.get("counted"):
                color = (0, 255, 0)  # Green = Counted
                status_text = "COUNTED"
            elif state.get("occupied"):
                color = (0, 255, 255)  # Yellow = Occupied
                status_text = f"OCCUPIED ({int(time.time() - state['timer_started'])}s)"
            else:
                color = (0, 0, 255)  # Red = Empty
                status_text = "EMPTY"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"Chair {zid}: {status_text}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
        if chair_setup_mode:
            cv2.putText(frame, "CHAIR SETUP MODE (Draw boxes, 's' to save, 'c' to exit)",
                        (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            if current_box:
                cv2.rectangle(frame, (current_box[0], current_box[1]), (current_box[2], current_box[3]), (255, 255, 255), 2)

    return frame


def run_pipeline(args):
    """
    Main detection pipeline.

    Reads frames, detects persons, tracks them, counts
    line crossings, saves data, and optionally displays output.
    """
    # ── Override config from CLI args ──
    source = args.source
    if source is not None:
        # Try to parse as integer (webcam index)
        try:
            source = int(source)
        except ValueError:
            pass  # Keep as string (file path or RTSP)
    else:
        source = config.VIDEO_SOURCE

    if args.confidence is not None:
        config.CONFIDENCE_THRESHOLD = args.confidence
    if args.frame_skip is not None:
        config.FRAME_SKIP = args.frame_skip

    show_display = config.DEBUG_MODE and not args.no_display

    # ── Initialize modules ──
    logger.info("=" * 50)
    logger.info("  Salon AI Monitoring System")
    logger.info("=" * 50)

    logger.info("Initializing modules...")

    stream = VideoStream(source=source)
    detector = PersonDetector()
    tracker = CentroidTracker()

    # Get actual frame dimensions after resize
    test_frame = None
    for _ in range(config.FRAME_SKIP + 1):
        test_frame = stream.read()
        if test_frame is not None:
            break

    if test_frame is not None:
        frame_height = test_frame.shape[0]
    else:
        frame_height = int(
            config.RESIZE_WIDTH *
            (stream.frame_height / max(stream.frame_width, 1))
        )

    counter = LineCrossingCounter(frame_height=frame_height)
    
    global chair_detector
    chair_detector = None
    if config.CHAIR_DETECTION_ENABLED:
        chair_detector = ChairDetector()

    storage = LocalStorage()

    # Optional Firebase storage
    firebase_storage = None
    if config.FIREBASE_ENABLED:
        from storage.firebase_storage import FirebaseStorage
        firebase_storage = FirebaseStorage()
        if firebase_storage.is_available():
            logger.info("Firebase storage active.")

    # ── Start dashboard ──
    dashboard_thread = None
    if config.DASHBOARD_AUTOSTART and not args.no_dashboard:
        dashboard_thread = start_dashboard_thread(storage)

    logger.info(f"Video source: {stream.get_info()}")
    logger.info(f"Detector: {detector.get_model_info()}")
    logger.info(f"Frame height: {frame_height}, Line Y: {counter.get_line_y()}")
    logger.info("Pipeline running. Press 'q' to quit.\n")

    # ── Main loop ──
    last_save_time = time.time()
    frame_process_count = 0
    fps_start_time = time.time()
    display_fps = 0.0

    # Graceful shutdown
    running = True

    def signal_handler(sig, frame_ref):
        nonlocal running
        running = False
        logger.info("Shutdown signal received.")

    signal.signal(signal.SIGINT, signal_handler)

    if show_display:
        cv2.namedWindow("Salon AI Monitor")
        if config.CHAIR_DETECTION_ENABLED:
            cv2.setMouseCallback("Salon AI Monitor", mouse_callback, param=chair_detector)

    try:
        while running and stream.is_opened():
            frame = stream.read()

            if frame is None:
                # Check if end of video file
                if stream.total_frames > 0:
                    remaining = stream.total_frames - stream.get_frame_count()
                    if remaining <= 0:
                        logger.info("End of video file reached.")
                        break
                continue

            frame_process_count += 1

            # ── Detect persons ──
            detections = detector.detect(frame)

            tracked_objects = {}
            bboxes = {}
            entries, exits = 0, 0
            counts = counter.get_counts()

            if config.ENABLE_TRACKING:
                # ── Update tracker ──
                tracked_objects = tracker.update(detections)
                bboxes = tracker.get_bboxes()

                # ── Update counter ──
                entries, exits = counter.update(tracked_objects)
                counts = counter.get_counts()
            else:
                # If tracking is disabled, just draw raw detections
                for i, det in enumerate(detections):
                    bboxes[i] = det[:4]

            chair_count = 0
            if config.CHAIR_DETECTION_ENABLED and chair_detector:
                newly_counted = chair_detector.update(bboxes)
                chair_count = chair_detector.get_counts()

                if newly_counted:
                    captures_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard", "static", "captures")
                    os.makedirs(captures_dir, exist_ok=True)
                    capture_frame = frame.copy()
                    
                    # Highlight the newly counted chairs on the frame
                    for zid in newly_counted:
                        for zone in chair_detector.get_zones():
                            if zone["id"] == zid:
                                x1, y1, x2, y2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]
                                cv2.rectangle(capture_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                                cv2.putText(capture_frame, f"Chair {zid} - CUSTOMER LOGGED", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                                break
                                
                    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                    for zid in newly_counted:
                        filename = f"chair_{zid}_{timestamp_str}.jpg"
                        filepath = os.path.join(captures_dir, filename)
                        cv2.imwrite(filepath, capture_frame)
                        logger.info(f"Saved capture for chair {zid} at {filepath}")

            total_customers = entries + chair_count

            # ── Update dashboard live data ──
            if not args.no_dashboard:
                try:
                    from dashboard.app import update_live_counts
                    update_live_counts(
                        entries=counts["entered"],
                        exits=counts["exited"],
                        in_store=counts["inside"],
                        persons_in_frame=len(tracked_objects) if config.ENABLE_TRACKING else len(detections),
                        chair_count=chair_count,
                        total_customers=total_customers
                    )
                except ImportError:
                    pass

            # ── Periodic save ──
            now = time.time()
            if config.ENABLE_TRACKING and now - last_save_time >= config.SAVE_INTERVAL:
                storage.save_count(entries=entries, exits=exits, chair_count=chair_count, total_customers=total_customers)
                if firebase_storage and firebase_storage.is_available():
                    firebase_storage.save_count(entries=entries, exits=exits) # Keeping firebase simple for now
                last_save_time = now
                logger.info(
                    f"Saved: entered={entries}, exited={exits}, "
                    f"inside={counts['inside']}, chair_count={chair_count}, total_customers={total_customers}"
                )

            # ── Calculate FPS ──
            elapsed = now - fps_start_time
            if elapsed >= 1.0:
                display_fps = frame_process_count / elapsed
                frame_process_count = 0
                fps_start_time = now

            # ── Display ──
            if show_display:
                display_frame = draw_overlay(
                    frame.copy(), tracked_objects, bboxes,
                    counter, detector.get_model_info()
                )

                # FPS counter
                cv2.putText(
                    display_frame,
                    f"FPS: {display_fps:.1f}",
                    (display_frame.shape[1] - 120, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2
                )

                cv2.imshow("Salon AI Monitor", display_frame)

                key = cv2.waitKey(1) & 0xFF
                global chair_setup_mode
                if key == ord('q'):
                    logger.info("Quit key pressed.")
                    break
                elif key == ord('r'):
                    counter.reset()
                    tracker.reset()
                    if chair_detector:
                        chair_detector.reset()
                    logger.info("Counters reset via keyboard.")
                elif key == ord('c') and config.CHAIR_DETECTION_ENABLED:
                    chair_setup_mode = not chair_setup_mode
                    logger.info(f"Chair setup mode: {'ON' if chair_setup_mode else 'OFF'}")
                elif key == ord('s') and config.CHAIR_DETECTION_ENABLED and chair_setup_mode:
                    if chair_detector:
                        chair_detector.save_config()
                    chair_setup_mode = False
                    logger.info("Chair config saved and setup mode exited.")
                elif key == ord('z') and config.CHAIR_DETECTION_ENABLED and chair_setup_mode:
                    if chair_detector:
                        chair_detector.clear_zones()
                    logger.info("Cleared all chair zones.")

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)

    finally:
        # ── Cleanup ──
        logger.info("Shutting down...")

        # Final save
        counts = counter.get_counts()
        if config.ENABLE_TRACKING:
            storage.save_count(
                entries=counts["entered"],
                exits=counts["exited"],
                chair_count=chair_detector.get_counts() if chair_detector else 0,
                total_customers=counts["entered"] + (chair_detector.get_counts() if chair_detector else 0)
            )
            if firebase_storage and firebase_storage.is_available():
                firebase_storage.save_count(
                    entries=counts["entered"],
                    exits=counts["exited"]
                )

        stream.release()
        if show_display:
            cv2.destroyAllWindows()

        logger.info(
            f"Final counts — Entered: {counts['entered']}, "
            f"Exited: {counts['exited']}, "
            f"Inside: {counts['inside']}"
        )
        logger.info("Salon AI Monitoring System stopped.")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    args = parse_args()
    run_pipeline(args)
