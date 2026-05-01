"""
Person Detection Module
========================
Uses YOLOv8 (ultralytics) to detect persons in video frames.
Only detects the "person" class (COCO class index 0) for efficiency.

Usage:
    detector = PersonDetector()
    detections = detector.detect(frame)
    # detections = [(x1, y1, x2, y2, confidence), ...]
"""

import logging
from ultralytics import YOLO
import config

logger = logging.getLogger(__name__)


class PersonDetector:
    """
    Lightweight person detector using YOLOv8.
    
    Loads a pre-trained YOLOv8 model (default: yolov8n — nano)
    and runs inference filtered to person class only.
    """

    # COCO dataset class index for "person"
    PERSON_CLASS_ID = 0

    def __init__(self, model_path=None, confidence=None):
        """
        Initialize the detector.

        Args:
            model_path (str, optional): Path to YOLO model weights.
                Defaults to config.YOLO_MODEL.
            confidence (float, optional): Minimum detection confidence.
                Defaults to config.CONFIDENCE_THRESHOLD.
        """
        self.model_path = model_path or config.YOLO_MODEL
        self.confidence = confidence or config.CONFIDENCE_THRESHOLD

        logger.info(f"Loading YOLO model: {self.model_path}")
        self.model = YOLO(self.model_path)
        logger.info("YOLO model loaded successfully.")

    def detect(self, frame):
        """
        Detect persons in a single frame.

        Args:
            frame (numpy.ndarray): BGR image frame from OpenCV.

        Returns:
            list[tuple]: List of detections, each as
                (x1, y1, x2, y2, confidence) where coordinates
                are pixel values of the bounding box.
        """
        # Run YOLO inference — filter to person class only
        results = self.model.predict(
            source=frame,
            classes=[self.PERSON_CLASS_ID],
            conf=self.confidence,
            verbose=False,  # Suppress per-frame YOLO logs
        )

        detections = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue

            for box in boxes:
                # Extract bounding box coordinates (xyxy format)
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())

                detections.append((
                    int(x1), int(y1),
                    int(x2), int(y2),
                    round(conf, 3)
                ))

        if config.VERBOSE:
            logger.debug(f"Detected {len(detections)} person(s)")

        return detections

    def get_model_info(self):
        """Return basic model metadata for diagnostics."""
        return {
            "model": self.model_path,
            "confidence_threshold": self.confidence,
            "device": "cpu",
        }
