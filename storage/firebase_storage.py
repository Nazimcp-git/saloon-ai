"""
Firebase Storage Module (Optional)
====================================
Cloud storage integration using Firebase Firestore.
Only active when config.FIREBASE_ENABLED is True.

This module has NO hard dependency on firebase-admin.
If the package is not installed, it logs a warning and
all methods become no-ops.

Usage:
    storage = FirebaseStorage()
    if storage.is_available():
        storage.save_count(entries=5, exits=2)
"""

import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)

# ── Conditional Firebase import ──
_firebase_available = False
_db = None

if config.FIREBASE_ENABLED:
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        # Initialize Firebase app (only once)
        if not firebase_admin._apps:
            cred = credentials.Certificate(config.FIREBASE_KEY_PATH)
            firebase_admin.initialize_app(cred)

        _db = firestore.client()
        _firebase_available = True
        logger.info("Firebase Firestore initialized successfully.")

    except ImportError:
        logger.warning(
            "firebase-admin package not installed. "
            "Install it with: pip install firebase-admin"
        )
    except Exception as e:
        logger.warning(f"Firebase initialization failed: {e}")


class FirebaseStorage:
    """
    Firebase Firestore storage for count data.
    
    Gracefully handles missing firebase-admin package.
    Interface matches LocalStorage for interchangeability.
    """

    def __init__(self, collection=None):
        """
        Initialize Firebase storage.

        Args:
            collection (str, optional): Firestore collection name.
                Defaults to config.FIREBASE_COLLECTION.
        """
        self.collection = collection or config.FIREBASE_COLLECTION
        self._available = _firebase_available

        if self._available:
            self._db = _db
            logger.info(f"Firebase storage ready: collection={self.collection}")
        else:
            logger.info("Firebase storage unavailable — operating as no-op.")

    def is_available(self):
        """Check if Firebase is properly configured and available."""
        return self._available

    def save_count(self, entries, exits, timestamp=None):
        """
        Save a count record to Firestore.

        Args:
            entries (int): Total entry count.
            exits (int): Total exit count.
            timestamp (str, optional): ISO timestamp. Defaults to now.
        """
        if not self._available:
            return

        if timestamp is None:
            timestamp = datetime.now().isoformat()

        date_str = datetime.now().strftime("%Y-%m-%d")

        record = {
            "timestamp": timestamp,
            "date": date_str,
            "entries": entries,
            "exits": exits,
            "in_store": max(0, entries - exits),
        }

        try:
            self._db.collection(self.collection).add(record)
            if config.VERBOSE:
                logger.debug(f"Firebase: saved record {record}")
        except Exception as e:
            logger.error(f"Firebase save failed: {e}")

    def get_today_counts(self):
        """
        Get all count records for today from Firestore.

        Returns:
            dict: {"date": str, "records": list[dict]}
        """
        if not self._available:
            return {"date": datetime.now().strftime("%Y-%m-%d"), "records": []}

        date_str = datetime.now().strftime("%Y-%m-%d")

        try:
            docs = (
                self._db.collection(self.collection)
                .where("date", "==", date_str)
                .order_by("timestamp")
                .stream()
            )
            records = [doc.to_dict() for doc in docs]
            return {"date": date_str, "records": records}

        except Exception as e:
            logger.error(f"Firebase query failed: {e}")
            return {"date": date_str, "records": []}

    def get_hourly_data(self, date_str=None):
        """
        Aggregate counts by hour from Firestore.

        Returns:
            dict: {"hours": [0-23], "entries": [counts], "exits": [counts]}
        """
        if not self._available:
            return {"hours": list(range(24)), "entries": [0]*24, "exits": [0]*24}

        if date_str is None:
            date_str = datetime.now().strftime("%Y-%m-%d")

        try:
            docs = (
                self._db.collection(self.collection)
                .where("date", "==", date_str)
                .stream()
            )

            hourly_entries = [0] * 24
            hourly_exits = [0] * 24

            for doc in docs:
                data = doc.to_dict()
                try:
                    ts = datetime.fromisoformat(data["timestamp"])
                    hour = ts.hour
                    hourly_entries[hour] = max(
                        hourly_entries[hour], data.get("entries", 0)
                    )
                    hourly_exits[hour] = max(
                        hourly_exits[hour], data.get("exits", 0)
                    )
                except (ValueError, KeyError):
                    continue

            return {
                "hours": list(range(24)),
                "entries": hourly_entries,
                "exits": hourly_exits,
            }

        except Exception as e:
            logger.error(f"Firebase hourly query failed: {e}")
            return {"hours": list(range(24)), "entries": [0]*24, "exits": [0]*24}

    def get_total_today(self):
        """Get total entries today from Firestore."""
        data = self.get_today_counts()
        if data["records"]:
            return data["records"][-1].get("entries", 0)
        return 0
