"""OAuth lifecycle management for Phantom Calendar."""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.file",
]

CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")


def get_credentials() -> Credentials:
    """Return valid OAuth credentials, running browser flow if needed.

    Raises:
        FileNotFoundError: if credentials.json does not exist.
    """
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"credentials.json not found at {CREDENTIALS_FILE}")

    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _write_token(creds)
        return creds

    # First run — launch browser consent flow
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    _write_token(creds)
    return creds


def _write_token(creds: Credentials) -> None:
    """Persist credentials to token.json with owner-only permissions."""
    with open(TOKEN_FILE, "w") as token:
        token.write(creds.to_json())
    os.chmod(TOKEN_FILE, 0o600)


def get_calendar_service():
    """Return an authorized Google Calendar API service."""
    creds = get_credentials()
    return build("calendar", "v3", credentials=creds)


def get_drive_service():
    """Return an authorized Google Drive API service."""
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)
