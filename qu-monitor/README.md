# QU Monitor - Weekly Stale QU Notifications

Automated monitoring system that checks for stale QUs (over 7 days old) in a Google Spreadsheet and sends weekly Slack DMs to team members.

## Overview

This bot monitors a Google Spreadsheet and:
1. Checks the "QU-PU" tab, Column C for dates
2. Identifies QUs that are over 7 days old
3. Counts stale QUs per person based on initials in Column B
4. Sends a Slack DM to each person: "Please reach out to X stale QUs"
5. Runs automatically every Monday at 9 AM UTC
6. Ignores rows where initials = "AH"

## ⭐ Setup: GitHub Actions (Recommended)

### Prerequisites

- Google Sheets API credentials (service account JSON file)
- Slack Bot Token with DM permissions
- Access to the QU spreadsheet

### Setup Instructions

#### 1. Configure Google Sheets API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API
4. Create a service account:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "QU Monitor")
   - Grant it "Viewer" role
   - Click "Done"
5. Create and download credentials:
   - Click on the service account
   - Go to "Keys" tab
   - Click "Add Key" > "Create new key"
   - Choose JSON format
   - Download the file
6. **Share the spreadsheet** with the service account email:
   - Open the service account JSON file
   - Find the `client_email` field
   - Go to your Google Spreadsheet
   - Click "Share" and add this email with "Viewer" permissions

#### 2. Configure Slack Bot

1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app or select an existing app
3. Add the following OAuth scopes under "OAuth & Permissions":
   - `chat:write` (send messages)
   - `im:write` (send DMs)
4. Install the app to your workspace
5. Copy the "Bot User OAuth Token" (starts with `xoxb-`)

#### 3. Encode Google Credentials

Run the helper script to encode your credentials for GitHub Secrets:

```bash
python encode_credentials.py path/to/your/credentials.json
```

This will output a base64-encoded string. Copy this string.

#### 4. Add GitHub Secrets

1. Go to your GitHub repository
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret** and add each of these:

| Secret Name | Value | Where to get it |
|-------------|-------|-----------------|
| `QU_SLACK_BOT_TOKEN` | `xoxb-...` | From Slack OAuth (step 2) |
| `QU_SPREADSHEET_ID` | `1ZNToizoyOjilIC6so2JQC-BGKrygOSuJYqEtPL4-_eM` | From spreadsheet URL |
| `QU_SHEET_NAME` | `QU-PU` | Name of the tab |
| `QU_GOOGLE_CREDENTIALS_JSON` | `eyJhbGc...` (base64 string) | From step 3 |

#### 5. Enable GitHub Actions

1. Go to your repository's **Actions** tab
2. If Actions are disabled, enable them
3. You should see the "QU Monitor" workflow

#### 6. Test the Workflow

1. Go to **Actions** tab
2. Click on "QU Monitor" workflow
3. Click **Run workflow** > **Run workflow**
4. Watch the logs to ensure it runs successfully

## How It Works

### Schedule
- Runs every Monday at 9 AM UTC
- Can be manually triggered from GitHub Actions

### Logic
1. Reads all rows from the "QU-PU" tab starting from row 1
2. For each row:
   - Reads Column B (initials) - takes first initial if multiple
   - Reads Column C (date)
   - Skips if initials = "AH"
   - Checks if date is more than 7 days old
3. Counts stale QUs per person
4. Sends a DM to each person with their count

### Date Formats Supported
The bot can parse dates in these formats:
- `12/04/2024` (MM/DD/YYYY)
- `2024-12-04` (YYYY-MM-DD)
- `12-04-2024` (MM-DD-YYYY)
- `04/12/2024` (DD/MM/YYYY)
- `12/04/24` (MM/DD/YY)
- `2024/12/04` (YYYY/MM/DD)

### Slack Message Format
```
Please reach out to X stale QUs
```
(Where X is the count)

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

### Ignored Initials

```python
IGNORED_INITIALS = ['AH']
```

### Stale Threshold

```python
STALE_DAYS = 7  # Days
```

## Modifying the Schedule

Edit `.github/workflows/qu-monitor.yml` and change the cron expression:

```yaml
schedule:
  - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC
```

Common schedules:
- Every Monday at 9 AM: `'0 9 * * 1'`
- Every Friday at 5 PM: `'0 17 * * 5'`
- Every day at 10 AM: `'0 10 * * *'`
- Twice a week (Mon & Thu): Use two cron entries

Use [crontab.guru](https://crontab.guru/) to create custom schedules.

**Note:** GitHub Actions uses UTC time. Adjust accordingly for your timezone.

## Local Testing

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
SPREADSHEET_ID=1ZNToizoyOjilIC6so2JQC-BGKrygOSuJYqEtPL4-_eM
SHEET_NAME=QU-PU
GOOGLE_CREDENTIALS_PATH=credentials.json
```

### 3. Run the Monitor

```bash
python qu_monitor.py
```

## Files

- `qu_monitor.py` - Main monitoring script
- `config.py` - User mappings and configuration
- `requirements.txt` - Python dependencies
- `encode_credentials.py` - Helper to encode Google credentials
- `.github/workflows/qu-monitor.yml` - GitHub Actions workflow
- `.env.example` - Example environment variables

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

3. Commit and push:

```bash
git add config.py
git commit -m "Add new team member to QU monitor"
git push
```

## Troubleshooting

### "Error reading spreadsheet"
- Ensure the spreadsheet is shared with the service account email
- Check that `QU_SPREADSHEET_ID` secret is correct
- Verify the sheet name is exactly "QU-PU"

### "Error authenticating"
- Verify `QU_GOOGLE_CREDENTIALS_JSON` secret is the base64-encoded credentials
- Re-run `encode_credentials.py` and update the secret

### "Error sending Slack DM"
- Verify `QU_SLACK_BOT_TOKEN` is correct (should start with `xoxb-`)
- Check bot has `chat:write` and `im:write` permissions
- Note: Users must allow DMs from apps in their Slack settings

### "Could not parse date"
- Check that Column C contains valid dates in a supported format
- The bot will log warnings for unparsable dates

### "Unknown initials"
- Update `USER_MAPPING` in `config.py` with new team members
- Ensure initials in spreadsheet match keys in USER_MAPPING

## Viewing Logs

### GitHub Actions
1. Go to **Actions** tab
2. Click on the latest "QU Monitor" run
3. Click on the "check-stale-qus" job
4. Expand "Run QU Monitor" to see logs

### Local
Logs are printed to console when running locally.

## Security Notes

- Never commit `.env` or `credentials.json` to git
- GitHub Secrets are encrypted and only exposed during workflow runs
- Use minimal permissions for the service account (Viewer is sufficient)
- Keep your Slack bot token secure

## License

Internal use only
