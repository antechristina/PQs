#!/usr/bin/env python3
"""
Helper script to encode Google Sheets credentials to base64 for GitHub Secrets

Usage:
    python encode_credentials.py credentials.json
"""

import base64
import sys
import json


def encode_credentials(file_path):
    """Encode a JSON credentials file to base64"""
    try:
        # Read the credentials file
        with open(file_path, 'r') as f:
            credentials = f.read()

        # Validate it's valid JSON
        json.loads(credentials)

        # Encode to base64
        encoded = base64.b64encode(credentials.encode()).decode()

        print("=" * 80)
        print("Base64-encoded credentials (copy this to GitHub Secrets):")
        print("=" * 80)
        print(encoded)
        print("=" * 80)
        print(f"\nLength: {len(encoded)} characters")
        print("\nTo add to GitHub:")
        print("1. Go to your repository on GitHub")
        print("2. Click Settings > Secrets and variables > Actions")
        print("3. Click 'New repository secret'")
        print("4. Name: GOOGLE_CREDENTIALS_JSON")
        print("5. Value: Paste the encoded string above")
        print("6. Click 'Add secret'")

        return encoded

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: File '{file_path}' is not valid JSON")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) != 2:
        print("Usage: python encode_credentials.py <credentials.json>")
        print("\nExample:")
        print("  python encode_credentials.py credentials.json")
        sys.exit(1)

    credentials_file = sys.argv[1]
    encode_credentials(credentials_file)


if __name__ == '__main__':
    main()
