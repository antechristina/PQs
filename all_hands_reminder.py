#!/usr/bin/env python3
"""
All Hands Reminder
Sends weekly reminder to update All Hands action items
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import List

from dotenv import load_dotenv
from config import USER_MAPPING

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# State file to track last notification time
STATE_FILE = 'all_hands_state.json'

# Pacific Time (UTC-8)
PACIFIC_TZ = timezone(timedelta(hours=-8))

# Additional users for weekly All Hands reminder only (not tracked in PQs)
ALL_HANDS_ADDITIONAL_USERS = {
    'MS': 'U07LTN9NE4S',
    'EJ': 'U082E1NT33Q',
}


class NotificationState:
    """Manages the state of notifications to track timing intervals"""

    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> dict:
        """Load notification state from file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading state file: {e}")
                return {}
        return {}

    def _save_state(self):
        """Save notification state to file"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving state file: {e}")

    def should_notify(self, key: str, interval_seconds: int) -> bool:
        """Check if enough time has passed since last notification"""
        if key not in self.state:
            return True

        last_notification = datetime.fromisoformat(self.state[key])
        now_pacific = datetime.now(PACIFIC_TZ)

        # Make last_notification timezone-aware if it isn't already
        if last_notification.tzinfo is None:
            last_notification = last_notification.replace(tzinfo=PACIFIC_TZ)

        time_since_last = now_pacific - last_notification

        return time_since_last.total_seconds() >= interval_seconds

    def mark_notified(self, key: str):
        """Mark a notification as sent with current timestamp (Pacific Time)"""
        self.state[key] = datetime.now(PACIFIC_TZ).isoformat()
        self._save_state()
        logger.info(f"Marked {key} as notified at {self.state[key]}")


class SlackNotifier:
    """Client for sending Slack notifications via webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        logger.info("Slack webhook client initialized")

    def send_weekly_all_hands_reminder(self, user_ids: List[str]) -> bool:
        """Send weekly All Hands reminder to all users"""
        try:
            # Build message tagging all users
            user_tags = " ".join([f"<@{user_id}>" for user_id in user_ids])
            message = f"{user_tags} Please update the statuses of all your action items in the All Hands document. This MUST be done 24h before All Hands meeting"

            payload = {
                "text": message
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            response.raise_for_status()
            logger.info(f"Sent weekly All Hands reminder to {len(user_ids)} user(s)")
            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Slack message: {e}")
            return False


class AllHandsReminder:
    """Main class for sending All Hands reminders"""

    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Initialize configuration
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL', '').strip()

        # Validate configuration
        self._validate_config()

        # Initialize clients
        self.slack_client = SlackNotifier(self.slack_webhook_url)
        self.notification_state = NotificationState()

        logger.info("All Hands Reminder initialized successfully")

    def _validate_config(self):
        """Validate required configuration"""
        if not self.slack_webhook_url:
            logger.error("Missing required environment variable: SLACK_WEBHOOK_URL")
            raise ValueError("Missing required environment variable: SLACK_WEBHOOK_URL")

    def send_reminder(self):
        """Send the All Hands reminder"""
        try:
            weekly_reminder_key = "weekly_all_hands_reminder"

            # Check if we should send weekly reminder (once per week = 604800 seconds)
            if self.notification_state.should_notify(weekly_reminder_key, 604800):
                # Get all user IDs except CC, plus additional All Hands users (MS, EJ)
                pq_user_ids = [user_id for initials, user_id in USER_MAPPING.items() if initials != 'CC']
                additional_user_ids = list(ALL_HANDS_ADDITIONAL_USERS.values())
                all_user_ids = pq_user_ids + additional_user_ids

                success = self.slack_client.send_weekly_all_hands_reminder(all_user_ids)
                if success:
                    self.notification_state.mark_notified(weekly_reminder_key)
                    logger.info("Sent weekly All Hands reminder successfully")
                else:
                    logger.error("Failed to send weekly All Hands reminder")
                    sys.exit(1)
            else:
                logger.info("Weekly All Hands reminder already sent this week, skipping")

        except Exception as e:
            logger.error(f"Error sending All Hands reminder: {e}")
            raise


def main():
    """Main entry point"""
    try:
        reminder = AllHandsReminder()
        reminder.send_reminder()
    except Exception as e:
        logger.error(f"Failed to send reminder: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
