# PQs Spreadsheet Monitor

Automated monitoring system for the PQs Google Spreadsheet that sends Slack notifications to team members who need to update their ETAs.

## Overview

This script monitors a Google Spreadsheet and:
1. Checks Column E (ETA) starting from row 3
2. If Column E is empty, checks Column C for team member initials
3. Sends a Slack notification to #ctc-bot-update every 3 hours tagging the person
4. Tracks notification state to avoid spam

## Prerequisites

- Python 3.7 or higher
- Google Sheets API credentials (service account JSON file)
- Slack Bot Token with permissions to post in channels
- Access to the PQs spreadsheet

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name and description
   - Grant it "Editor" role
   - Create a JSON key and download it
5. Save the JSON key as `credentials.json` in this directory
6. Share your Google Spreadsheet with the service account email (found in the JSON file)

### 3. Configure Slack Bot

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app or use an existing bot
3. Add the following OAuth scopes:
   - `chat:write`
   - `channels:read`
4. Install the app to your workspace
5. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
6. Invite the bot to #ctc-bot-update channel: `/invite @your-bot-name`

### 4. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your credentials:
   ```
   SLACK_BOT_TOKEN=xoxb-your-actual-token
   SLACK_CHANNEL=ctc-bot-update
   SPREADSHEET_ID=1dDYU1rGKYiiXxcJlYnh4lmM5UBJBPqtYIstZsiJG-ng
   SHEET_NAME=Sheet1
   GOOGLE_CREDENTIALS_PATH=credentials.json
   NOTIFICATION_INTERVAL=10800
   CHECK_INTERVAL=300
   ```

### 5. Verify Configuration

The user mapping is already configured in `config.py`:
```python
USER_MAPPING = {
    'CF': 'U096E94CPSQ',
    'DI': 'U02S7HKMLEQ',
    'JS': 'U01UYJGCDT9',
    'RD': 'U07B2J0JQ04',
    'CTC': 'U09E4C6S5GS',
    'CC': 'U01Q1DPP4UX',
    'JC': 'U0248V5LYV6',
    'SR': 'U02QMUE0ELV',
}
```

## Usage

### Run the Monitor

```bash
python pq_monitor.py
```

The script will:
- Check the spreadsheet every 5 minutes (configurable)
- Send notifications every 3 hours to users with missing ETAs
- Log all activity to `pq_monitor.log` and console
- Track notification state in `notification_state.json`

### Run in Background

To run the script continuously in the background:

```bash
# Using nohup
nohup python pq_monitor.py > output.log 2>&1 &

# Or using screen
screen -S pq_monitor
python pq_monitor.py
# Press Ctrl+A, then D to detach
```

### Stop the Monitor

```bash
# If running in foreground
Ctrl+C

# If running with nohup, find the process
ps aux | grep pq_monitor.py
kill <PID>

# If using screen
screen -r pq_monitor
# Then Ctrl+C
```

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `NOTIFICATION_INTERVAL` | Seconds between notifications to same user | 10800 (3 hours) |
| `CHECK_INTERVAL` | Seconds between spreadsheet checks | 300 (5 minutes) |
| `SLACK_CHANNEL` | Slack channel for notifications | ctc-bot-update |
| `SHEET_NAME` | Name of the sheet tab | Sheet1 |
| `START_ROW` | First row to check (in config.py) | 3 |

## How It Works

1. **Spreadsheet Monitoring**: The script reads rows starting from row 3, checking columns C (initials) and E (ETA)

2. **Notification Logic**:
   - If Column E is empty AND Column C has valid initials → notify user
   - If Column E has a value → clear notification state (no spam if they update)
   - If Column C is empty → skip row

3. **State Tracking**:
   - `notification_state.json` tracks when each row was last notified
   - Ensures 3-hour minimum between notifications per row
   - Automatically clears when ETA is filled

4. **Slack Message Format**:
   ```
   @username please update your ETA in the PQs (Row 5)
   ```

## Files

- `pq_monitor.py` - Main monitoring script
- `config.py` - User mappings and column configuration
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (create from .env.example)
- `credentials.json` - Google Sheets API credentials (you provide)
- `notification_state.json` - Auto-generated state tracking file
- `pq_monitor.log` - Auto-generated log file

## Troubleshooting

### "Credentials file not found"
- Ensure `credentials.json` exists in the project directory
- Update `GOOGLE_CREDENTIALS_PATH` in `.env` if using different name/location

### "Permission denied" when reading spreadsheet
- Share the spreadsheet with the service account email
- Service account email is in `credentials.json` under `client_email`

### Slack notifications not sending
- Verify bot token is correct in `.env`
- Ensure bot is invited to #ctc-bot-update channel
- Check bot has `chat:write` permission

### "Unknown initials" warning
- Update `USER_MAPPING` in `config.py` with new team members
- Ensure initials in spreadsheet match keys in USER_MAPPING exactly

## Adding New Team Members

Edit `config.py` and add to `USER_MAPPING`:

```python
USER_MAPPING = {
    # Existing users...
    'NEW': 'U0XXXXXXXXXXX',  # New person's Slack User ID
}
```

To find Slack User IDs:
1. Open Slack
2. Click on user's profile
3. Click "More" > "Copy member ID"

## Security Notes

- Never commit `.env` or `credentials.json` to git
- These files are in `.gitignore` by default
- Keep your Slack bot token and Google credentials secure

## License

Internal use only
