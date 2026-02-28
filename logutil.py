import os
import sys
from datetime import datetime

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}


def _ok(level: str) -> bool:
    return _LEVELS.get(level, 20) >= _LEVELS.get(LOG_LEVEL, 20)


def log(level: str, msg: str) -> None:
    level = level.upper()
    if not _ok(level):
        return
    ts = datetime.now().strftime("%H:%M:%S")
    sys.stderr.write(f"[{ts}] {level:<5} {msg}\n")
    sys.stderr.flush()


def debug(msg: str) -> None:
    log("DEBUG", msg)


def info(msg: str) -> None:
    log("INFO", msg)


def warn(msg: str) -> None:
    log("WARN", msg)


def error(msg: str) -> None:
    log("ERROR", msg)
