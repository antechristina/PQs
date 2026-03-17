#!/usr/bin/env python3
"""
Google Sheet to Slack
Reads rows from a Google Sheet where column H = 1 and posts
columns B, C, E, F as a list to a Slack channel.
"""

import os
import sys
import logging
import requests

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

SPREADSHEET_ID = '1dDYU1rGKYiiXxcJlYnh4lmM5UBJBPqtYIstZsiJG-ng'
SLACK_CHANNEL_ID = 'C08TX1PATPE'

# Column indices (0-based): B=1, C=2, E=4, F=5, H=7
COL_B = 1
COL_C = 2
COL_E = 4
COL_F = 5
COL_H = 7


def get_sheets_service():
    import base64
    import json as _json

    creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON', '').strip()
    creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'credentials.json')

    if creds_json:
        try:
            if creds_json.startswith('ey') or len(creds_json) > 500:
                try:
                    creds_info = _json.loads(base64.b64decode(creds_json))
                except Exception:
                    creds_info = _json.loads(creds_json)
            else:
                creds_info = _json.loads(creds_json)
            creds = ServiceAccountCredentials.from_service_account_info(creds_info, scopes=SCOPES)
        except Exception as e:
            logger.error(f"Error parsing GOOGLE_CREDENTIALS_JSON: {e}")
            raise
    elif os.path.exists(creds_path):
        creds = ServiceAccountCredentials.from_service_account_file(creds_path, scopes=SCOPES)
    else:
        raise ValueError("No Google credentials provided: set GOOGLE_CREDENTIALS_JSON or GOOGLE_CREDENTIALS_PATH")

    return build('sheets', 'v4', credentials=creds)


def fetch_rows(service, sheet_name: str = 'Sheet1') -> list:
    """Fetch all rows from the sheet."""
    try:
        result = (
            service.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range=sheet_name)
            .execute()
        )
        return result.get('values', [])
    except HttpError as e:
        logger.error(f"Google Sheets API error: {e}")
        raise


def get_cell(row: list, index: int) -> str:
    """Safely get a cell value from a row."""
    if index < len(row):
        return str(row[index]).strip()
    return ''


def build_slack_message(matching_rows: list) -> str:
    """Format matching rows as a Slack list, grouped by date."""
    if not matching_rows:
        return "No rows found with column H = 1."

    header = "*Upcoming Launch G2M ETAs:*"

    # Group rows by date (column E), preserving order
    from collections import OrderedDict
    groups = OrderedDict()
    for row in matching_rows:
        date = get_cell(row, COL_E)
        groups.setdefault(date, []).append(row)

    sub_labels = 'abcdefghijklmnopqrstuvwxyz'
    lines = []
    for number, (date, rows) in enumerate(groups.items(), start=1):
        for i, row in enumerate(rows):
            b = get_cell(row, COL_B)
            c = get_cell(row, COL_C)
            f = get_cell(row, COL_F)
            if i == 0:
                lines.append(f"{number}. ({c}) {b} ({date} {f})")
            else:
                label = sub_labels[i - 1] if (i - 1) < len(sub_labels) else str(i)
                lines.append(f"    {label}. ({c}) {b} ({date} {f})")

    return f"<!here>\n{header}\n" + "\n".join(lines)


def post_to_slack(token: str, channel: str, message: str) -> bool:
    """Post a message to a Slack channel using the bot token."""
    response = requests.post(
        'https://slack.com/api/chat.postMessage',
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        json={'channel': channel, 'text': message},
        timeout=10,
    )
    data = response.json()
    if not data.get('ok'):
        logger.error(f"Slack API error: {data.get('error')}")
        return False
    logger.info(f"Message posted to {channel}")
    return True


def main():
    load_dotenv()

    slack_token = os.getenv('SLACK_BOT_TOKEN', '').strip()
    if not slack_token:
        logger.error("Missing required environment variable: SLACK_BOT_TOKEN")
        sys.exit(1)

    sheet_name = os.getenv('SHEET_NAME', 'Sheet1')

    service = get_sheets_service()
    rows = fetch_rows(service, sheet_name)
    logger.info(f"Fetched {len(rows)} rows from sheet")

    matching = [row for row in rows if get_cell(row, COL_H) == '1']
    logger.info(f"Found {len(matching)} row(s) with column H = 1")

    message = build_slack_message(matching)
    success = post_to_slack(slack_token, SLACK_CHANNEL_ID, message)
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
