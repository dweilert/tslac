from __future__ import annotations

from pathlib import Path

# ----------------------------
# Config
# ----------------------------
BASE = "https://www.tsl.texas.gov"
HOME = f"{BASE}/"
NEWS = f"{BASE}/info"

APP_DIR = Path(__file__).resolve().parent
OUT_DIR = APP_DIR / "output"
STATE_DIR = APP_DIR / "state"

CANDIDATES_FILE = OUT_DIR / "candidates_latest.json"
SELECTED_FILE = APP_DIR / "selected.yaml"
CURATION_FILE = APP_DIR / "curation.yaml"
WATCH_FILE = APP_DIR / "watch.yaml"
WATCH_RESULTS_FILE = OUT_DIR / "watch_results_latest.json"

HOST = "127.0.0.1"
PORT = 5055

HEADERS = {"User-Agent": "newsletter-bot/1.0 (local script)"}

DEFAULT_SUBJECT = "Monthly Update — New from the Texas State Library"
DEFAULT_INTRO = (
    "Hello everyone—here are highlights and resources recently published by the Texas State Library "
    "and Archives Commission."
)

# ----------------------------
# Filtering rules
# ----------------------------
EXACT_EXCLUDE_PATHS = {
    "/contact",
    "/visit",
    "/about",
    "/tslac-statutesandrules",
    "/libsearch",
    "/arc",
    "/tbp",
    "/slrm",
    # "/txbookchat",  # removed per your request
}

EXCLUDE_TEXTS = {
    "see more news and events",
    "view our calendar",
    "subscribe to events",
}

LAST_3_MONTHS_DAYS = 92
