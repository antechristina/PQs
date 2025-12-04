# PQs Spreadsheet Monitor

Automated monitoring system for the PQs Google Spreadsheet that sends Slack notifications to team members who need to update their ETAs.

## Overview

This script monitors a Google Spreadsheet and:
1. Checks Column E (ETA) starting from row 3
2. If Column E is empty, checks Column C for team member initials
3. Sends a Slack notification to #ctc-bot-update every 3 hours tagging the person
4. Tracks notification state to avoid spam

## ⭐ Recommended Setup: GitHub Actions (No Local Machine Required)

The easiest way to run this monitor is using GitHub Actions, which runs automatically on a schedule without requiring your computer to be on.

### Prerequisites

- Google Sheets API credentials (service account JSON file)
- Slack Bot Token with permissions to post in channels
- Access to the PQs spreadsheet

### Setup Instructions

#### 1. Configure Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "PQ Monitor")
   - Grant it "Viewer" role (minimal permissions needed)
   - Click "Done"
5. Create and download credentials:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the file (save it somewhere safe temporarily)
6. **Share the spreadsheet** with the service account email:
   - Open the service account JSON file
   - Find the `client_email` field (looks like `xxxxx@xxxxx.iam.gserviceaccount.com`)
   - Go to your Google Spreadsheet
   - Click "Share" and add this email with "Viewer" permissions

#### 2. Configure Slack Bot

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app or use an existing bot
3. Add the following OAuth scopes under "OAuth & Permissions":
   - `chat:write`
   - `channels:read`
4. Install the app to your workspace
5. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
6. Invite the bot to #ctc-bot-update channel in Slack:
   ```
   /invite @your-bot-name
   ```

#### 3. Encode Google Credentials

Run the helper script to encode your credentials for GitHub Secrets:

```bash
python encode_credentials.py path/to/your/credentials.json
```

This will output a base64-encoded string. Copy this string - you'll need it in the next step.

**You can delete the credentials.json file after encoding** - you won't need it anymore!

#### 4. Add GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret** and add each of these:

| Secret Name | Value | Where to get it |
|-------------|-------|-----------------|
| `SLACK_BOT_TOKEN` | `xoxb-...` | From Slack API (step 2) |
| `SLACK_CHANNEL` | `ctc-bot-update` | Your Slack channel name |
| `SPREADSHEET_ID` | `1dDYU1rGKYiiXxcJlYnh4lmM5UBJBPqtYIstZsiJG-ng` | From spreadsheet URL |
| `SHEET_NAME` | `Sheet1` | Name of the tab in your spreadsheet |
| `GOOGLE_CREDENTIALS_JSON` | `eyJhbGc...` (base64 string) | From step 3 |
| `NOTIFICATION_INTERVAL` | `10800` | Seconds (10800 = 3 hours) |

#### 5. Enable GitHub Actions

1. Go to your repository's **Actions** tab
2. If Actions are disabled, click the button to enable them
3. You should see the "PQs Monitor" workflow

#### 6. Test the Workflow

1. Go to **Actions** tab
2. Click on "PQs Monitor" workflow
3. Click **Run workflow** > **Run workflow**
4. Watch the logs to ensure it runs successfully

### How It Works (GitHub Actions)

- **Schedule**: Runs automatically every hour
- **Notifications**: Only sends messages every 3 hours per person (respects `NOTIFICATION_INTERVAL`)
- **State Persistence**: Uses GitHub Actions cache to remember who was notified and when
- **No Cost**: GitHub Actions is free for public repos, and 2000 minutes/month for private repos

### Modifying the Schedule

Edit `.github/workflows/pq-monitor.yml` and change the cron expression:

```yaml
schedule:
  - cron: '0 * * * *'  # Every hour at minute 0
```

Common schedules:
- Every hour: `'0 * * * *'`
- Every 30 minutes: `'*/30 * * * *'`
- Every 3 hours: `'0 */3 * * *'`
- Every day at 9 AM: `'0 9 * * *'`

Use [crontab.guru](https://crontab.guru/) to create custom schedules.

---

## Alternative: Local Setup (Requires Computer Always On)

If you prefer to run this on your local machine or a server:

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:
```
SLACK_BOT_TOKEN=xoxb-your-actual-token
SLACK_CHANNEL=ctc-bot-update
SPREADSHEET_ID=1dDYU1rGKYiiXxcJlYnh4lmM5UBJBPqtYIstZsiJG-ng
SHEET_NAME=Sheet1
GOOGLE_CREDENTIALS_PATH=credentials.json
NOTIFICATION_INTERVAL=10800
CHECK_INTERVAL=300
```

### 3. Run the Monitor

```bash
# Continuous mode (runs forever)
python pq_monitor.py

# Run in background
nohup python pq_monitor.py > output.log 2>&1 &
```

---

## Configuration

### User Mapping

The mapping of initials to Slack User IDs is in `config.py`:

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

### Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `NOTIFICATION_INTERVAL` | Seconds between notifications to same user | 10800 (3 hours) |
| `CHECK_INTERVAL` | Seconds between spreadsheet checks (local only) | 300 (5 minutes) |
| `SLACK_CHANNEL` | Slack channel for notifications | ctc-bot-update |
| `SHEET_NAME` | Name of the sheet tab | Sheet1 |
| `START_ROW` | First row to check (in config.py) | 3 |

## How It Works

### Spreadsheet Monitoring
The script reads rows starting from row 3, checking columns C (initials) and E (ETA).

### Notification Logic
- If Column E is empty AND Column C has valid initials → notify user
- If Column E has a value → clear notification state (no spam if they update)
- If Column C is empty → skip row

### State Tracking
- `notification_state.json` tracks when each row was last notified
- Ensures 3-hour minimum between notifications per row
- Automatically clears when ETA is filled
- In GitHub Actions, this file is cached between runs

### Slack Message Format
```
@username please update your ETA in the PQs (Row 5)
```

## Files

- `pq_monitor.py` - Main monitoring script
- `config.py` - User mappings and column configuration
- `requirements.txt` - Python dependencies
- `encode_credentials.py` - Helper to encode Google credentials for GitHub
- `.github/workflows/pq-monitor.yml` - GitHub Actions workflow
- `.env.example` - Example environment variables (for local setup)
- `notification_state.json` - Auto-generated state tracking file

## Adding New Team Members

1. Get their Slack User ID:
   - Open Slack
   - Click on user's profile
   - Click "More" > "Copy member ID"

2. Edit `config.py` and add to `USER_MAPPING`:

```python
USER_MAPPING = {
    # Existing users...
    'NEW': 'U0XXXXXXXXXXX',  # New person's Slack User ID
}
```

3. Commit and push the change:

```bash
git add config.py
git commit -m "Add new team member to PQ monitor"
git push
```

The GitHub Action will automatically use the updated mapping on the next run.

## Troubleshooting

### GitHub Actions Issues

**"Error reading spreadsheet"**
- Ensure the spreadsheet is shared with the service account email
- Check that `SPREADSHEET_ID` secret is correct

**"Error authenticating"**
- Verify `GOOGLE_CREDENTIALS_JSON` secret is the base64-encoded credentials
- Re-run `encode_credentials.py` and update the secret if needed

**"Error sending Slack message"**
- Verify `SLACK_BOT_TOKEN` is correct (should start with `xoxb-`)
- Ensure bot is invited to the channel specified in `SLACK_CHANNEL` secret
- Check bot has `chat:write` permission

**Workflow not running on schedule**
- GitHub Actions may delay scheduled workflows by a few minutes during high load
- You can always trigger manually from the Actions tab

### Local Setup Issues

**"Credentials file not found"**
- Ensure `credentials.json` exists in the project directory
- Update `GOOGLE_CREDENTIALS_PATH` in `.env`

**"Permission denied" when reading spreadsheet**
- Share the spreadsheet with the service account email
- Service account email is in `credentials.json` under `client_email`

### Common Issues

**"Unknown initials" warning**
- Update `USER_MAPPING` in `config.py` with new team members
- Ensure initials in spreadsheet match keys in USER_MAPPING exactly (case-sensitive)

**Not receiving notifications**
- Check that Column E is actually empty
- Check that Column C has valid initials from the mapping
- Verify that 3 hours have passed since the last notification

## Viewing Logs

### GitHub Actions
1. Go to **Actions** tab
2. Click on the latest "PQs Monitor" run
3. Click on the "check-pqs" job
4. Expand "Run PQ Monitor" to see logs

### Local
Logs are printed to console when running locally.

## Security Notes

- Never commit `.env` or `credentials.json` to git (they're in `.gitignore`)
- GitHub Secrets are encrypted and only exposed during workflow runs
- Use minimal permissions for the service account (Viewer is sufficient)
- Keep your Slack bot token secure

## License

Internal use only
