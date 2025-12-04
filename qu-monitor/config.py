"""
Configuration file for QU Slack notification system
"""

# Mapping of initials to Slack User IDs
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

# Initials to ignore
IGNORED_INITIALS = ['AH', 'CC']

# Column indices (0-based)
COLUMN_B_INDEX = 1  # Initials column
COLUMN_C_INDEX = 2  # Date column

# Starting row (1-based, will be converted to 0-based in code)
START_ROW = 1

# Stale threshold in days
STALE_DAYS = 7
