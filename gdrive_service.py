from __future__ import annotations

from pathlib import Path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from logutil import debug, info

SCOPES = ["https://www.googleapis.com/auth/drive"]

TOKEN_FILE = "token.json"
CREDENTIALS_FILE = "credentials.json"
FOLDER_STATE_FILE = "state/gdrive_folders.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]  # full access (needed to move files)

ROOT = Path(__file__).resolve().parent
CREDENTIALS_PATH = ROOT / "credentials.json"
TOKEN_PATH = ROOT / "token.json"


# def get_drive_service():
#     creds = None
#     info("GDrive: initializing service")
#     ...
#     if os.path.exists(TOKEN_FILE):
#         debug("GDrive: found token.json, loading credentials")
#     ...
#     if not creds or not creds.valid:
#         info("GDrive: credentials missing/invalid; starting refresh/login flow")
#         ...
#         info("GDrive: credentials obtained; token.json updated")
#     else:
#         debug("GDrive: credentials valid")

#     info("GDrive: service ready")
#     return build("drive", "v3", credentials=creds)


def get_drive_service():
    """
    Uses OAuth installed-app flow:
      - credentials.json: your client_id/client_secret file from Google Cloud Console
      - token.json: generated after you authorize in the browser
    """
    if not CREDENTIALS_PATH.exists():
        raise RuntimeError(f"Missing credentials.json at {CREDENTIALS_PATH}")

    creds = None
    if TOKEN_PATH.exists():
        debug(f"GDrive: loading token from {TOKEN_PATH}")
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        info("GDrive: token missing/invalid, starting OAuth browser flow")
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
        creds = flow.run_local_server(port=0)
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
        debug(f"GDrive: wrote new token to {TOKEN_PATH}")

    info("GDrive: building Drive v3 service")
    return build("drive", "v3", credentials=creds)


def find_folder_id(service, folder_name: str) -> str:
    debug(f"GDrive: resolving folder name '{folder_name}'")
    q = (
        f"name='{folder_name}' and "
        "mimeType='application/vnd.google-apps.folder' and "
        "trashed=false"
    )
    res = service.files().list(q=q, fields="files(id,name)", pageSize=10).execute()
    files = res.get("files", [])
    if not files:
        raise RuntimeError(f"Drive folder not found: {folder_name}")
    if len(files) > 1:
        raise RuntimeError(f"Multiple Drive folders named '{folder_name}'. Rename to unique.")

    debug(f"GDrive: folder '{folder_name}' -> id={files[0]['id']}")
    return files[0]["id"]


def list_files_in_folder(service, folder_id: str):
    q = f"'{folder_id}' in parents and trashed=false"
    res = (
        service.files()
        .list(
            q=q,
            fields="files(id,name,mimeType,modifiedTime,size)",
            pageSize=50,
        )
        .execute()
    )
    return res.get("files", [])
