"""
Chair Detection Module
=======================
Handles optional chair-based customer counting.
Detects when a person sits in a configured chair zone for a minimum duration.

Usage:
    detector = ChairDetector()
    detector.update(bboxes)
"""

import os
import json
import time
import logging
import config

logger = logging.getLogger(__name__)

class ChairDetector:
    def __init__(self):
        self.zones = []
        self.states = {}
        self.chair_count = 0
        self.config_path = config.CHAIR_CONFIG_PATH
        self.min_sitting_time = config.CHAIR_MIN_SITTING_TIME
        
        self.load_config()

    def load_config(self):
        """Load chair zones from JSON file or fallback to config.py."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.zones = json.load(f)
                logger.info(f"Loaded {len(self.zones)} chair zones from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load chair config: {e}")
                self.zones = config.CHAIR_ZONES.copy()
        else:
            self.zones = config.CHAIR_ZONES.copy()
            logger.info(f"Loaded {len(self.zones)} default chair zones from config.py")

        self._init_states()

    def save_config(self):
        """Save current chair zones to JSON file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.zones, f, indent=4)
            logger.info(f"Saved {len(self.zones)} chair zones to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save chair config: {e}")

    def _init_states(self):
        """Initialize state tracking for each chair."""
        self.states = {}
        for zone in self.zones:
            self.states[zone["id"]] = {
                "occupied": False,
                "timer_started": None,
                "counted": False,
                "last_seen": None
            }

    def add_zone(self, x1, y1, x2, y2):
        """Add a new chair zone manually."""
        new_id = 1
        if self.zones:
            new_id = max(z["id"] for z in self.zones) + 1
            
        self.zones.append({
            "id": new_id,
            "x1": min(x1, x2),
            "y1": min(y1, y2),
            "x2": max(x1, x2),
            "y2": max(y1, y2)
        })
        self._init_states()
        self.save_config()  # Auto-save permanently when added
        logger.info(f"Added new chair zone ID: {new_id} and saved to config.")

    def clear_zones(self):
        """Remove all configured chair zones."""
        self.zones = []
        self.states = {}
        logger.info("Cleared all chair zones.")

    def update(self, bboxes):
        """
        Check occupancy for each chair zone based on person bounding boxes.
        
        Args:
            bboxes (list or dict): Bounding boxes of detected persons.
                Can be raw detections list [(x1,y1,x2,y2,conf), ...] or
                tracker dict {id: (x1,y1,x2,y2)}.
        """
        # Extract just the (x1, y1, x2, y2) tuples
        if isinstance(bboxes, dict):
            box_list = list(bboxes.values())
        else:
            box_list = [b[:4] for b in bboxes]

        now = time.time()
        newly_counted = []

        for zone in self.zones:
            zone_id = zone["id"]
            state = self.states[zone_id]
            
            zx1, zy1, zx2, zy2 = zone["x1"], zone["y1"], zone["x2"], zone["y2"]
            is_currently_occupied = False

            # Check if any person is in this chair
            for box in box_list:
                px1, py1, px2, py2 = [int(v) for v in box]
                
                # Use centroid of the person for overlap logic
                cx = (px1 + px2) // 2
                cy = (py1 + py2) // 2

                # If centroid is inside the chair zone, consider it occupied
                if zx1 <= cx <= zx2 and zy1 <= cy <= zy2:
                    is_currently_occupied = True
                    break

            if is_currently_occupied:
                state["last_seen"] = now
                if not state["occupied"]:
                    # Person just entered the chair
                    state["occupied"] = True
                    state["timer_started"] = now
                    logger.debug(f"Chair {zone_id} occupied. Timer started.")
                else:
                    # Person has been in the chair
                    elapsed = now - state["timer_started"]
                    if elapsed >= self.min_sitting_time and not state["counted"]:
                        # Confirm as a customer!
                        self.chair_count += 1
                        state["counted"] = True
                        newly_counted.append(zone_id)
                        logger.info(f"Chair {zone_id} counted as customer! Total chair count: {self.chair_count}")
            else:
                if state["occupied"]:
                    # 5-second patience to prevent flickering from resetting the timer or double counting
                    if state["last_seen"] is not None and (now - state["last_seen"] > 5.0):
                        # Person definitively left the chair
                        state["occupied"] = False
                        state["timer_started"] = None
                        state["counted"] = False
                        state["last_seen"] = None
                        logger.debug(f"Chair {zone_id} emptied. State reset.")
        
        return newly_counted

    def get_counts(self):
        """Return the total number of customers counted via chairs."""
        return self.chair_count

    def get_zones(self):
        """Return the list of chair zones."""
        return self.zones

    def get_states(self):
        """Return the current states of all chairs for drawing."""
        return self.states

    def reset(self):
        """Reset the counter but keep the zones."""
        self.chair_count = 0
        self._init_states()
        logger.info("Chair detector counter reset.")
