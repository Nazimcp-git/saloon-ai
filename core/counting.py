"""
Line-Crossing Counter Module
==============================
Counts persons entering/exiting by detecting when tracked
centroids cross a configurable horizontal line.

Prevents double-counting by tracking which IDs have already
been counted.

Usage:
    counter = LineCrossingCounter(frame_height=480)
    entries, exits = counter.update(tracked_objects)
"""

import logging
import time

import config

logger = logging.getLogger(__name__)


class LineCrossingCounter:
    """
    Counts entries and exits based on line-crossing detection.

    A horizontal line divides the frame. When a tracked person's
    centroid crosses from one side to the other, it counts as
    an entry or exit depending on the configured direction.
    """

    def __init__(self, frame_height=480):
        """
        Initialize the counter.

        Args:
            frame_height (int): Height of the video frame in pixels.
                Used to compute the actual line Y position from the
                fractional LINE_POSITION config value.
        """
        self.frame_height = frame_height
        self.line_y = int(frame_height * config.LINE_POSITION)
        self.direction = config.DIRECTION_MODE  # "entry", "exit", or "both"
        self.buffer = config.MIN_MOVEMENT_THRESHOLD

        # Cumulative counts
        self.entry_count = 0
        self.exit_count = 0

        # Previous centroid Y positions: {object_id: previous_cy}
        self._previous_positions = {}

        # Set of object IDs that have already been counted
        # (prevents double-counting if person lingers near line)
        self._counted_ids = set()

        # Timestamp of last count event (for logging)
        self._last_event_time = None

        logger.info(
            f"Counter initialized: line_y={self.line_y}, "
            f"direction={self.direction}, frame_height={frame_height}"
        )

    def update(self, tracked_objects):
        """
        Check for line crossings and update counts.

        Args:
            tracked_objects (dict): {object_id: (cx, cy)} from the tracker.

        Returns:
            tuple: (total_entries, total_exits) cumulative counts.
        """
        current_ids = set(tracked_objects.keys())

        for object_id, (cx, cy) in tracked_objects.items():
            # Skip if this ID was already counted
            if object_id in self._counted_ids:
                continue

            # Need a previous position to detect crossing
            if object_id in self._previous_positions:
                prev_cy = self._previous_positions[object_id]

                # ── Detect line crossing with Entry Zone Filtering ──
                # Person must move completely from outside the buffer zone
                # to the other side outside the buffer zone.
                crossed = False
                is_entry = False

                # Top to bottom movement
                if prev_cy < self.line_y - self.buffer and cy > self.line_y + self.buffer:
                    if self.direction in ["entry", "both"]:
                        crossed = True
                        is_entry = True

                # Bottom to top movement
                elif prev_cy > self.line_y + self.buffer and cy < self.line_y - self.buffer:
                    if self.direction in ["exit", "both"]:
                        crossed = True
                        is_entry = False

                if crossed:
                    if is_entry:
                        self.entry_count += 1
                        logger.info(
                            f"ENTRY detected: ID={object_id}, "
                            f"total_entered={self.entry_count}"
                        )
                    else:
                        self.exit_count += 1
                        logger.info(
                            f"EXIT detected: ID={object_id}, "
                            f"total_exited={self.exit_count}"
                        )

                    self._counted_ids.add(object_id)
                    self._last_event_time = time.time()

            # Update previous position
            self._previous_positions[object_id] = cy

        # ── Cleanup: remove positions for objects no longer tracked ──
        # This resets the double-counting logic when a person leaves the frame
        stale_ids = set(self._previous_positions.keys()) - current_ids
        for stale_id in stale_ids:
            del self._previous_positions[stale_id]
            if stale_id in self._counted_ids:
                self._counted_ids.remove(stale_id)

        return self.entry_count, self.exit_count

    def get_counts(self):
        """
        Get current cumulative counts.

        Returns:
            dict: {"entered": int, "exited": int, "inside": int}
        """
        return {
            "entered": self.entry_count,
            "exited": self.exit_count,
            "inside": max(0, self.entry_count - self.exit_count),
        }

    def get_line_y(self):
        """Return the Y pixel coordinate of the counting line."""
        return self.line_y

    def reset(self):
        """Reset all counts and tracked positions."""
        self.entry_count = 0
        self.exit_count = 0
        self._previous_positions.clear()
        self._counted_ids.clear()
        self._last_event_time = None
        logger.info("Counter reset.")

    def update_frame_height(self, new_height):
        """Recalculate line position for a new frame height."""
        self.frame_height = new_height
        self.line_y = int(new_height * config.LINE_POSITION)
        logger.info(f"Line position updated: line_y={self.line_y}")
