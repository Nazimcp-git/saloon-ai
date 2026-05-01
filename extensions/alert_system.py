"""
Alert System Extension (Stub)
===============================
Optional module for triggering alerts based on customer activity.

STATUS: Stub — not fully implemented.
Designed for email, webhook, or local notification alerts.

Example triggers:
    - Customer detected but no billing activity
    - Store occupancy exceeds threshold
    - No customers detected during business hours

Usage:
    ext = AlertSystem(max_occupancy=20)
    ext.check(current_counts)
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AlertSystem:
    """
    Alert system extension stub.
    
    Monitors customer counts and triggers alerts based on
    configurable rules. Supports multiple alert channels.
    """

    def __init__(self, max_occupancy=20, alert_cooldown=300):
        """
        Initialize the alert system.

        Args:
            max_occupancy (int): Maximum allowed in-store count.
            alert_cooldown (int): Minimum seconds between alerts
                of the same type to prevent spam.
        """
        self.max_occupancy = max_occupancy
        self.alert_cooldown = alert_cooldown
        self._last_alerts = {}
        self.enabled = False

        logger.info(
            "AlertSystem extension loaded (stub — not implemented). "
            "Call enable() and configure alert channels to activate."
        )

    def enable(self):
        """Enable the alert system."""
        self.enabled = True
        logger.info("Alert system enabled.")

    def check(self, counts):
        """
        Check current counts against alert rules.

        Args:
            counts (dict): {"entries": int, "exits": int, "in_store": int}

        Returns:
            list[dict]: Triggered alerts, each with type and message.
        """
        if not self.enabled:
            return []

        alerts = []

        # ── Rule: Occupancy threshold ──
        if counts.get("in_store", 0) > self.max_occupancy:
            alert = self._create_alert(
                alert_type="high_occupancy",
                message=(
                    f"⚠️ High occupancy: {counts['in_store']} people "
                    f"(max: {self.max_occupancy})"
                ),
            )
            if alert:
                alerts.append(alert)

        # TODO: Add more rules
        # - No billing activity alert
        # - Empty store during business hours
        # - Unusual traffic patterns

        return alerts

    def _create_alert(self, alert_type, message):
        """
        Create an alert if cooldown has passed.

        Returns:
            dict or None: Alert dict, or None if in cooldown.
        """
        now = datetime.now()

        if alert_type in self._last_alerts:
            elapsed = (now - self._last_alerts[alert_type]).total_seconds()
            if elapsed < self.alert_cooldown:
                return None

        self._last_alerts[alert_type] = now

        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": now.isoformat(),
        }

        logger.warning(f"ALERT: {message}")
        self._send_alert(alert)

        return alert

    def _send_alert(self, alert):
        """
        Send alert through configured channels.

        TODO: Implement alert delivery:
            - Email (via smtplib or external API)
            - Webhook (HTTP POST to Slack, Discord, etc.)
            - Desktop notification
            - SMS (via Twilio or similar)
        """
        logger.info(f"Alert would be sent: {alert['message']}")
        # Example:
        # requests.post(webhook_url, json=alert)
        # send_email(subject=alert['type'], body=alert['message'])
