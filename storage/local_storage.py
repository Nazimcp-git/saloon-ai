"""
Local Storage Module
=====================
Saves customer count data to local JSON and CSV files.
Provides methods to retrieve today's data and hourly aggregates.

Data is organized by date in the configured DATA_DIR:
    data/
        counts_2025-01-15.json
        counts_2025-01-15.csv

Usage:
    storage = LocalStorage()
    storage.save_count(entries=5, exits=2)
    today = storage.get_today_counts()
"""

import os
import json
import csv
import logging
from datetime import datetime, timedelta
from threading import Lock

import config

logger = logging.getLogger(__name__)


class LocalStorage:
    """
    Thread-safe local file storage for count data.
    
    Saves to both JSON (for programmatic access) and CSV (for easy export).
    """

    def __init__(self, data_dir=None):
        """
        Initialize local storage.

        Args:
            data_dir (str, optional): Directory to store data files.
                Defaults to config.DATA_DIR.
        """
        self.data_dir = data_dir or config.DATA_DIR
        self._lock = Lock()

        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(f"Local storage initialized: {self.data_dir}")

    def _get_date_str(self):
        """Current date as YYYY-MM-DD string."""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_json_path(self, date_str=None):
        """Path to the JSON file for a given date."""
        date_str = date_str or self._get_date_str()
        return os.path.join(self.data_dir, f"counts_{date_str}.json")

    def _get_csv_path(self, date_str=None):
        """Path to the CSV file for a given date."""
        date_str = date_str or self._get_date_str()
        return os.path.join(self.data_dir, f"counts_{date_str}.csv")

    def _load_json(self, date_str=None):
        """Load JSON data for a given date, or return empty structure."""
        path = self._get_json_path(date_str)
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load {path}: {e}")
        return {"date": date_str or self._get_date_str(), "records": []}

    def save_count(self, entries, exits, timestamp=None, chair_count=0, total_customers=0):
        """
        Save a count record with timestamp.

        Args:
            entries (int): Total entry count.
            exits (int): Total exit count.
            timestamp (str, optional): ISO format timestamp.
            chair_count (int, optional): Count of customers from chairs.
            total_customers (int, optional): Total combined customers.
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        record = {
            "timestamp": timestamp,
            "entered": entries,
            "exited": exits,
            "inside": max(0, entries - exits),
            "chair_count": chair_count,
            "total_customers": total_customers if total_customers else entries + chair_count,
        }

        with self._lock:
            self._save_to_json(record)
            self._save_to_csv(record)

        if config.VERBOSE:
            logger.debug(f"Saved count: {record}")

    def _save_to_json(self, record):
        """Append a record to today's JSON file."""
        data = self._load_json()
        data["records"].append(record)

        path = self._get_json_path()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _save_to_csv(self, record):
        """Append a record to today's CSV file."""
        path = self._get_csv_path()
        file_exists = os.path.exists(path)

        with open(path, "a", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["timestamp", "entered", "exited", "inside", "chair_count", "total_customers"]
            )
            if not file_exists:
                writer.writeheader()
            writer.writerow(record)

    def get_today_counts(self):
        """
        Get all count records for today.

        Returns:
            dict: {"date": str, "records": list[dict]}
        """
        return self._load_json()

    def get_latest_count(self):
        """
        Get the most recent count record for today.

        Returns:
            dict or None: Latest record, or None if no data.
        """
        data = self._load_json()
        if data["records"]:
            return data["records"][-1]
        return None

    def get_hourly_data(self, date_str=None):
        """
        Aggregate counts by hour for charting.

        Returns hourly maximum entry counts for the given date.

        Args:
            date_str (str, optional): Date in YYYY-MM-DD format.
                Defaults to today.

        Returns:
            dict: {"hours": [0-23], "entered": [counts], "exited": [counts]}
        """
        data = self._load_json(date_str)
        
        # Initialize hourly buckets
        hourly_entries = [0] * 24
        hourly_exits = [0] * 24

        for record in data.get("records", []):
            try:
                ts = datetime.fromisoformat(record["timestamp"])
                hour = ts.hour
                # Use max entries/exits seen in each hour
                hourly_entries[hour] = max(
                    hourly_entries[hour], record.get("entered", 0)
                )
                hourly_exits[hour] = max(
                    hourly_exits[hour], record.get("exited", 0)
                )
            except (ValueError, KeyError) as e:
                logger.warning(f"Skipping malformed record: {e}")

        return {
            "hours": list(range(24)),
            "entered": hourly_entries,
            "exited": hourly_exits,
        }

    def get_total_today(self):
        """
        Get the total entry count for today.

        Returns:
            int: Total entries today (from the latest record).
        """
        latest = self.get_latest_count()
        if latest:
            return latest.get("total_customers", latest.get("entered", 0))
        return 0

    def clear_today(self):
        """Delete today's data files (useful for reset)."""
        date_str = self._get_date_str()
        for path in [self._get_json_path(date_str), self._get_csv_path(date_str)]:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Deleted: {path}")
