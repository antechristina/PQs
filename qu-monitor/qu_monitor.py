#!/usr/bin/env python3
"""
QU Monitor - Weekly Slack notifications for stale QUs
Monitors a Google Spreadsheet and sends DMs to team members about stale QUs
"""

import os
import sys
import json
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import USER_MAPPING, IGNORED_INITIALS, COLUMN_B_INDEX, COLUMN_C_INDEX, START_ROW, STALE_DAYS

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
    """Client for sending Slack DMs"""

    def __init__(self, token: str):
        self.client = WebClient(token=token)
        logger.info("Slack client initialized")

    def send_dm(self, user_id: str, message: str) -> bool:
        """Send a DM to a user"""
        try:
            response = self.client.chat_postMessage(
                channel=user_id,
                text=message
            )

            logger.info(f"Sent DM to user {user_id}")
            return response['ok']

        except SlackApiError as e:
            logger.error(f"Error sending Slack DM: {e.response['error']}")
            return False


class QUMonitor:
    """Main monitor class that checks for stale QUs and sends notifications"""

    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Initialize configuration - strip whitespace to handle copy/paste issues
        self.spreadsheet_id = os.getenv('SPREADSHEET_ID', '').strip()
        self.sheet_name = os.getenv('SHEET_NAME', 'QU-PU').strip()
        self.slack_token = os.getenv('SLACK_BOT_TOKEN', '').strip()

        # Validate configuration
        self._validate_config()

        # Initialize clients - support both file and env var credentials
        google_creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', '').strip()
        google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip()

        self.sheets_client = GoogleSheetsClient(
            credentials_path=google_creds_path if google_creds_path else None,
            credentials_json=google_creds_json if google_creds_json else None
        )
        self.slack_client = SlackNotifier(self.slack_token)

        logger.info("QU Monitor initialized successfully")

    def _validate_config(self):
        """Validate required configuration"""
        required_vars = [
            'SLACK_BOT_TOKEN',
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

    def parse_date(self, date_str: str) -> datetime:
        """Parse date string in various formats"""
        if not date_str:
            return None

        # Try common date formats
        formats = [
            '%m/%d/%Y',      # 12/04/2024
            '%Y-%m-%d',      # 2024-12-04
            '%m-%d-%Y',      # 12-04-2024
            '%d/%m/%Y',      # 04/12/2024
            '%m/%d/%y',      # 12/04/24
            '%Y/%m/%d',      # 2024/12/04
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def get_first_initials(self, initials_str: str) -> str:
        """Extract first initials from a string (handles comma or space separated)"""
        if not initials_str:
            return ''

        # Split by comma or space and get first
        initials = initials_str.replace(',', ' ').split()
        return initials[0].strip().upper() if initials else ''

    def check_and_notify(self):
        """Check the spreadsheet and send notifications for stale QUs"""
        try:
            # Read all data from the sheet
            range_notation = f"A{START_ROW}:C"
            rows = self.sheets_client.read_sheet_data(
                self.spreadsheet_id,
                self.sheet_name,
                range_notation
            )

            if not rows:
                logger.info("No data found in spreadsheet")
                return

            # Count stale QUs per person
            stale_counts = defaultdict(int)
            today = datetime.now()
            cutoff_date = today - timedelta(days=STALE_DAYS)

            logger.info(f"Checking for QUs older than {cutoff_date.strftime('%Y-%m-%d')}")

            for idx, row in enumerate(rows):
                row_number = START_ROW + idx

                # Ensure row has enough columns
                while len(row) < max(COLUMN_B_INDEX, COLUMN_C_INDEX) + 1:
                    row.append('')

                initials_str = row[COLUMN_B_INDEX].strip() if len(row) > COLUMN_B_INDEX else ''
                date_str = row[COLUMN_C_INDEX].strip() if len(row) > COLUMN_C_INDEX else ''

                # Get first initials
                initials = self.get_first_initials(initials_str)

                # Skip if no initials or ignored initials
                if not initials or initials in IGNORED_INITIALS:
                    continue

                # Parse date
                date_obj = self.parse_date(date_str)
                if not date_obj:
                    continue

                # Check if stale
                if date_obj < cutoff_date:
                    if initials in USER_MAPPING:
                        stale_counts[initials] += 1
                        logger.info(f"Row {row_number}: Found stale QU for {initials} (date: {date_str})")
                    else:
                        logger.warning(f"Row {row_number}: Unknown initials '{initials}'")

            # Send notifications
            logger.info(f"Stale QU counts: {dict(stale_counts)}")

            for initials, count in stale_counts.items():
                if count > 0:
                    user_id = USER_MAPPING[initials]
                    message = f"Please reach out to {count} stale QU{'s' if count != 1 else ''}"

                    success = self.slack_client.send_dm(user_id, message)
                    if success:
                        logger.info(f"Notified {initials} about {count} stale QU(s)")
                    else:
                        logger.error(f"Failed to notify {initials}")

            if not stale_counts:
                logger.info("No stale QUs found - no notifications sent")

            logger.info("Check completed successfully")

        except Exception as e:
            logger.error(f"Error during check and notify: {e}")
            raise


def main():
    """Main entry point"""
    try:
        monitor = QUMonitor()
        monitor.check_and_notify()
    except Exception as e:
        logger.error(f"Failed to run monitor: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
