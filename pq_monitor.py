#!/usr/bin/env python3
"""
PQs Spreadsheet Monitor
Monitors a Google Spreadsheet and sends Slack notifications for missing ETAs
"""

import os
import sys
import time
import json
import base64
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import USER_MAPPING, COLUMN_C_INDEX, COLUMN_E_INDEX, START_ROW

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Google Sheets API scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# State file to track last notification times
STATE_FILE = 'notification_state.json'


class NotificationState:
    """Manages the state of notifications to track timing intervals"""

    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> Dict:
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

    def should_notify(self, row_key: str, interval_seconds: int) -> bool:
        """Check if enough time has passed since last notification"""
        if row_key not in self.state:
            return True

        last_notification = datetime.fromisoformat(self.state[row_key])
        time_since_last = datetime.now() - last_notification

        return time_since_last.total_seconds() >= interval_seconds

    def mark_notified(self, row_key: str):
        """Mark a row as notified with current timestamp"""
        self.state[row_key] = datetime.now().isoformat()
        self._save_state()
        logger.info(f"Marked {row_key} as notified at {self.state[row_key]}")

    def clear_row(self, row_key: str):
        """Remove a row from notification state (e.g., when ETA is filled)"""
        if row_key in self.state:
            del self.state[row_key]
            self._save_state()
            logger.info(f"Cleared notification state for {row_key}")


class GoogleSheetsClient:
    """Client for interacting with Google Sheets API"""

    def __init__(self, credentials_path: str = None, credentials_json: str = None):
        self.credentials_path = credentials_path
        self.credentials_json = credentials_json
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Sheets API"""
        creds = None

        try:
            # Try credentials from environment variable (base64 encoded) first
            if self.credentials_json:
                try:
                    # Decode base64 if needed
                    if self.credentials_json.startswith('ey') or len(self.credentials_json) > 500:
                        # Looks like base64
                        try:
                            decoded = base64.b64decode(self.credentials_json)
                            creds_info = json.loads(decoded)
                        except:
                            # Maybe it's already JSON
                            creds_info = json.loads(self.credentials_json)
                    else:
                        creds_info = json.loads(self.credentials_json)

                    creds = ServiceAccountCredentials.from_service_account_info(
                        creds_info, scopes=SCOPES
                    )
                    logger.info("Authenticated with service account credentials from environment")
                except Exception as e:
                    logger.error(f"Error parsing credentials from environment: {e}")
                    raise
            # Try service account credentials from file
            elif self.credentials_path and os.path.exists(self.credentials_path):
                creds = ServiceAccountCredentials.from_service_account_file(
                    self.credentials_path, scopes=SCOPES
                )
                logger.info("Authenticated with service account credentials from file")
            else:
                logger.error("No credentials provided")
                raise ValueError("No credentials provided")

            self.service = build('sheets', 'v4', credentials=creds)
            logger.info("Google Sheets API client initialized")

        except Exception as e:
            logger.error(f"Error authenticating with Google Sheets: {e}")
            raise

    def read_sheet_data(self, spreadsheet_id: str, sheet_name: str, range_notation: str) -> List[List]:
        """Read data from a Google Sheet"""
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!{range_notation}"
            ).execute()

            values = result.get('values', [])
            logger.info(f"Read {len(values)} rows from spreadsheet")
            return values

        except HttpError as e:
            logger.error(f"Error reading spreadsheet: {e}")
            raise


class SlackNotifier:
    """Client for sending Slack notifications via webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        logger.info("Slack webhook client initialized")

    def send_notification(self, user_id: str, initials: str, row_number: int) -> bool:
        """Send a notification to a user via webhook"""
        try:
            message = f"<@{user_id}> please update your ETA in the PQs (Row {row_number})"

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
            logger.info(f"Sent notification to {initials} (User ID: {user_id}) for row {row_number}")
            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            logger.error(f"Error sending Slack message: {e}")
            return False


class PQMonitor:
    """Main monitor class that orchestrates the spreadsheet checking and notifications"""

    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Initialize configuration
        self.spreadsheet_id = os.getenv('SPREADSHEET_ID')
        self.sheet_name = os.getenv('SHEET_NAME', 'Sheet1')
        self.slack_webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        self.notification_interval = int(os.getenv('NOTIFICATION_INTERVAL', '10800'))  # 3 hours
        self.check_interval = int(os.getenv('CHECK_INTERVAL', '300'))  # 5 minutes

        # Validate configuration
        self._validate_config()

        # Initialize clients - support both file and env var credentials
        google_creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
        google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')

        self.sheets_client = GoogleSheetsClient(
            credentials_path=google_creds_path,
            credentials_json=google_creds_json
        )
        self.slack_client = SlackNotifier(self.slack_webhook_url)
        self.notification_state = NotificationState()

        logger.info("PQ Monitor initialized successfully")

    def _validate_config(self):
        """Validate required configuration"""
        required_vars = [
            'SLACK_WEBHOOK_URL',
            'SPREADSHEET_ID',
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        # Check that at least one credentials method is provided
        if not os.getenv('GOOGLE_CREDENTIALS_PATH') and not os.getenv('GOOGLE_CREDENTIALS_JSON'):
            logger.error("Missing Google credentials: provide either GOOGLE_CREDENTIALS_PATH or GOOGLE_CREDENTIALS_JSON")
            raise ValueError("Missing Google credentials: provide either GOOGLE_CREDENTIALS_PATH or GOOGLE_CREDENTIALS_JSON")

    def check_and_notify(self):
        """Check the spreadsheet and send notifications as needed"""
        try:
            # Read all data starting from row 3
            # We need columns A through E, starting from row 3
            range_notation = f"A{START_ROW}:E"
            rows = self.sheets_client.read_sheet_data(
                self.spreadsheet_id,
                self.sheet_name,
                range_notation
            )

            if not rows:
                logger.info("No data found in spreadsheet")
                return

            # Process each row
            for idx, row in enumerate(rows):
                actual_row_number = START_ROW + idx
                self._process_row(row, actual_row_number)

            logger.info(f"Completed check of {len(rows)} rows")

        except Exception as e:
            logger.error(f"Error during check and notify cycle: {e}")

    def _process_row(self, row: List, row_number: int):
        """Process a single row and send notification if needed"""
        # Ensure row has enough columns
        while len(row) < max(COLUMN_C_INDEX, COLUMN_E_INDEX) + 1:
            row.append('')

        column_c_value = row[COLUMN_C_INDEX].strip() if len(row) > COLUMN_C_INDEX else ''
        column_e_value = row[COLUMN_E_INDEX].strip() if len(row) > COLUMN_E_INDEX else ''

        row_key = f"row_{row_number}"

        # Check if Column E (ETA) is empty
        if not column_e_value:
            # Column E is empty, check Column C for initials
            if column_c_value and column_c_value in USER_MAPPING:
                # Found initials, check if we should send notification
                if self.notification_state.should_notify(row_key, self.notification_interval):
                    user_id = USER_MAPPING[column_c_value]
                    success = self.slack_client.send_notification(
                        user_id,
                        column_c_value,
                        row_number
                    )

                    if success:
                        self.notification_state.mark_notified(row_key)
                else:
                    logger.debug(f"Row {row_number}: Too soon to notify {column_c_value}")
            elif column_c_value:
                logger.warning(f"Row {row_number}: Unknown initials '{column_c_value}'")
        else:
            # Column E has a value, clear any notification state
            self.notification_state.clear_row(row_key)

    def run_once(self):
        """Run a single check cycle (for scheduled execution)"""
        logger.info("Starting PQ Monitor - Single Run Mode")
        logger.info(f"Notification interval: {self.notification_interval} seconds ({self.notification_interval / 3600} hours)")

        try:
            logger.info("Running check cycle...")
            self.check_and_notify()
            logger.info("Check cycle completed successfully")
        except Exception as e:
            logger.error(f"Error during check cycle: {e}")
            raise

    def run_continuous(self):
        """Main run loop for continuous operation (local use)"""
        logger.info("Starting PQ Monitor - Continuous Mode")
        logger.info(f"Checking spreadsheet every {self.check_interval} seconds")
        logger.info(f"Notification interval: {self.notification_interval} seconds ({self.notification_interval / 3600} hours)")

        try:
            while True:
                logger.info("Running check cycle...")
                self.check_and_notify()
                logger.info(f"Sleeping for {self.check_interval} seconds...")
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            raise


def main():
    """Main entry point"""
    try:
        monitor = PQMonitor()

        # Check if running in GitHub Actions or similar scheduled environment
        if os.getenv('GITHUB_ACTIONS') or os.getenv('RUN_ONCE'):
            monitor.run_once()
        else:
            monitor.run_continuous()
    except Exception as e:
        logger.error(f"Failed to start monitor: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
