# secrets_env.py
from __future__ import annotations

import os
import re
from pathlib import Path

# Repo root assumed to be the directory containing this file.
# If your layout differs, adjust ENV_PATH accordingly.
APP_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = APP_DIR / ".env"

_ENV_LINE_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")


def load_env(path: Path = ENV_PATH, *, override: bool = False) -> None:
    """
    Load KEY=VALUE pairs from .env into process env.
    - override=False: only set env var if not already set (safer for shells)
    - override=True: .env wins
    """
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        m = _ENV_LINE_RE.match(line)
        if not m:
            continue

        key, raw_val = m.group(1), m.group(2)

        # Strip surrounding quotes if present
        val = raw_val
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]

        if override or key not in os.environ:
            os.environ[key] = val


def read_secret(name: str, *, path: Path = ENV_PATH) -> str:
    """
    Returns the effective value:
      1) os.environ[name] if set
      2) value from .env if present
      3) "" otherwise
    """
    if os.getenv(name) is not None:
        return os.getenv(name, "")

    if not path.exists():
        return ""

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = _ENV_LINE_RE.match(line)
        if not m:
            continue
        key, raw_val = m.group(1), m.group(2)
        if key != name:
            continue

        val = raw_val.strip()
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        return val

    return ""


def _format_env_value(value: str) -> str:
    """
    Format a value safely for .env:
    - If it contains spaces, #, or quotes, wrap in double quotes and escape.
    """
    if value == "":
        return '""'

    needs_quotes = any(ch.isspace() for ch in value) or "#" in value or '"' in value or "'" in value
    if not needs_quotes:
        return value

    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def update_env(
    updates: dict[str, str],
    *,
    path: Path = ENV_PATH,
    create_if_missing: bool = True,
    keep_order: bool = True,
) -> None:
    """
    Update (or add) keys in .env.
    - Preserves comments and unknown lines.
    - If a key exists multiple times, only the first occurrence is updated.
    """
    if not path.exists():
        if not create_if_missing:
            raise FileNotFoundError(f"{path} does not exist")
        path.write_text("", encoding="utf-8")

    lines = path.read_text(encoding="utf-8").splitlines(keepends=False)

    seen: set[str] = set()
    out: list[str] = []

    for raw_line in lines:
        line = raw_line
        m = _ENV_LINE_RE.match(line.strip())
        if not m:
            out.append(raw_line)
            continue

        key = m.group(1)
        if key in updates and key not in seen:
            new_val = _format_env_value(updates[key])
            out.append(f"{key}={new_val}")
            seen.add(key)
        else:
            out.append(raw_line)

    # Append any new keys not found
    if keep_order:
        for key, val in updates.items():
            if key not in seen:
                out.append(f"{key}={_format_env_value(val)}")
    else:
        for key in sorted(updates.keys()):
            if key not in seen:
                out.append(f"{key}={_format_env_value(updates[key])}")

    # Ensure trailing newline
    text = "\n".join(out).rstrip("\n") + "\n"
    path.write_text(text, encoding="utf-8")


def mask_secret(value: str, *, show_last: int = 4) -> str:
    """
    For UI display: returns masked version like '••••abcd'.
    """
    if not value:
        return ""
    if len(value) <= show_last:
        return "•" * len(value)
    return ("•" * (len(value) - show_last)) + value[-show_last:]


def known_secret_keys() -> list[str]:
    """
    Central list for your app secrets.
    We can expand later.
    """
    return [
        "OPENAI_API_KEY",
        "TINYMCE_API_KEY",
    ]
