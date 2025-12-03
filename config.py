"""
Configuration file for PQs Slack notification system
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

# Column indices (0-based)
COLUMN_C_INDEX = 2  # Initials column
COLUMN_E_INDEX = 4  # ETA column

# Starting row (1-based, will be converted to 0-based in code)
START_ROW = 3
