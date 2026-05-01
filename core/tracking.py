"""
Centroid Tracking Module
=========================
Lightweight object tracker using centroid-based matching.
Assigns temporary IDs to detected persons and maintains
identity across frames using Euclidean distance.

No deep learning — pure numpy for maximum speed on CPU.

Usage:
    tracker = CentroidTracker()
    objects = tracker.update(bounding_boxes)
    # objects = {id: (cx, cy), ...}
"""

import logging
import numpy as np
from collections import OrderedDict

import config

logger = logging.getLogger(__name__)


class CentroidTracker:
    """
    Simple centroid-based multi-object tracker.
    
    Algorithm:
        1. Compute centroids of new detections.
        2. If no existing objects, register all as new.
        3. Otherwise, compute pairwise distances between
           existing centroids and new centroids.
        4. Match closest pairs (greedy assignment).
        5. Register unmatched detections as new objects.
        6. Mark unmatched existing objects as disappeared.
        7. Deregister objects that have disappeared for too long.
    """

    def __init__(self, max_disappeared=None, max_distance=None):
        """
        Initialize the tracker.

        Args:
            max_disappeared (int, optional): Max frames before deregistering.
                Defaults to config.MAX_DISAPPEARED.
            max_distance (float, optional): Max pixel distance for matching.
                Defaults to config.MAX_MATCH_DISTANCE.
        """
        self.max_disappeared = max_disappeared or config.MAX_DISAPPEARED
        self.max_distance = max_distance or config.MAX_MATCH_DISTANCE

        # Tracked objects: ID → centroid (cx, cy)
        self.objects = OrderedDict()

        # Bounding boxes for tracked objects: ID → (x1, y1, x2, y2)
        self.bboxes = OrderedDict()

        # Count of consecutive frames each object has been missing
        self.disappeared = OrderedDict()

        # Next unique ID to assign
        self._next_id = 0

    def _register(self, centroid, bbox):
        """Register a new object with a unique ID."""
        object_id = self._next_id
        self.objects[object_id] = centroid
        self.bboxes[object_id] = bbox
        self.disappeared[object_id] = 0
        self._next_id += 1

        if config.VERBOSE:
            logger.debug(f"Registered new object ID={object_id} at {centroid}")

        return object_id

    def _deregister(self, object_id):
        """Remove an object from tracking."""
        del self.objects[object_id]
        del self.bboxes[object_id]
        del self.disappeared[object_id]

        if config.VERBOSE:
            logger.debug(f"Deregistered object ID={object_id}")

    @staticmethod
    def _compute_centroid(bbox):
        """
        Compute the centroid of a bounding box.

        Args:
            bbox (tuple): (x1, y1, x2, y2)

        Returns:
            tuple: (cx, cy) center coordinates
        """
        x1, y1, x2, y2 = bbox[:4]
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        return (cx, cy)

    def update(self, detections):
        """
        Update tracker with new detections.

        Args:
            detections (list[tuple]): List of (x1, y1, x2, y2, conf)
                bounding boxes from the detector.

        Returns:
            OrderedDict: {object_id: (cx, cy)} — currently tracked objects.
        """
        # ── No detections: increment disappeared for all ──
        if len(detections) == 0:
            for object_id in list(self.disappeared.keys()):
                self.disappeared[object_id] += 1
                if self.disappeared[object_id] > self.max_disappeared:
                    self._deregister(object_id)
            return self.objects

        # ── Compute centroids for new detections ──
        input_centroids = []
        input_bboxes = []
        for det in detections:
            centroid = self._compute_centroid(det)
            input_centroids.append(centroid)
            input_bboxes.append(det[:4])

        input_centroids = np.array(input_centroids)

        # ── No existing objects: register all ──
        if len(self.objects) == 0:
            for i in range(len(input_centroids)):
                self._register(tuple(input_centroids[i]), input_bboxes[i])
            return self.objects

        # ── Match existing objects to new detections ──
        object_ids = list(self.objects.keys())
        object_centroids = np.array(list(self.objects.values()))

        # Compute pairwise Euclidean distances
        # Shape: (num_existing, num_new)
        distances = np.linalg.norm(
            object_centroids[:, np.newaxis] - input_centroids[np.newaxis, :],
            axis=2
        )

        # Greedy matching: sort by distance, assign closest pairs
        rows = distances.min(axis=1).argsort()
        cols = distances.argmin(axis=1)[rows]

        used_rows = set()
        used_cols = set()

        for (row, col) in zip(rows, cols):
            if row in used_rows or col in used_cols:
                continue

            # Reject match if distance is too large
            if distances[row, col] > self.max_distance:
                continue

            object_id = object_ids[row]
            self.objects[object_id] = tuple(input_centroids[col])
            self.bboxes[object_id] = input_bboxes[col]
            self.disappeared[object_id] = 0

            used_rows.add(row)
            used_cols.add(col)

        # ── Handle unmatched existing objects ──
        unused_rows = set(range(len(object_ids))) - used_rows
        for row in unused_rows:
            object_id = object_ids[row]
            self.disappeared[object_id] += 1
            if self.disappeared[object_id] > self.max_disappeared:
                self._deregister(object_id)

        # ── Register unmatched new detections ──
        unused_cols = set(range(len(input_centroids))) - used_cols
        for col in unused_cols:
            self._register(tuple(input_centroids[col]), input_bboxes[col])

        return self.objects

    def get_bboxes(self):
        """Return current bounding boxes for all tracked objects."""
        return dict(self.bboxes)

    def reset(self):
        """Clear all tracked objects."""
        self.objects.clear()
        self.bboxes.clear()
        self.disappeared.clear()
        self._next_id = 0
        logger.info("Tracker reset.")
