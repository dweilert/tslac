# logutil.py
import os
import sys
import traceback
from datetime import datetime

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}


def _ok(level: str) -> bool:
    return _LEVELS.get(level, 20) >= _LEVELS.get(LOG_LEVEL, 20)


def log(level: str, msg: str, *, exc_info: bool = False) -> None:
    level = level.upper()
    if not _ok(level):
        return

    ts = datetime.now().strftime("%H:%M:%S")
    sys.stderr.write(f"[{ts}] {level:<5} {msg}\n")

    if exc_info:
        # If we're in an exception handler, this prints the active traceback.
        tb = traceback.format_exc()
        if tb and tb != "NoneType: None\n":
            sys.stderr.write(tb)

    sys.stderr.flush()


def debug(msg: str) -> None:
    log("DEBUG", msg)


def info(msg: str) -> None:
    log("INFO", msg)


def warn(msg: str) -> None:
    log("WARN", msg)


def error(msg: str, *, exc_info: bool = False) -> None:
    log("ERROR", msg, exc_info=exc_info)
