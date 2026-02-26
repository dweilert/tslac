#!/usr/bin/env python3ython

from __future__ import annotations
from annotated_types import doc
from dotenv import load_dotenv
from logutil import info
from http.server import HTTPServer
from config import HOST, PORT, OUT_DIR, STATE_DIR
from server import Handler

# macOS TLS fix: validate like curl (Keychain trust store)
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

load_dotenv()


def run_server():
    httpd = HTTPServer((HOST, PORT), Handler)
    info(f"Server running on http://{HOST}:{PORT}")
    info(f"Open that URL in a browser. Use 'Refresh candidates' to fetch latest.")
    httpd.serve_forever()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    run_server()


if __name__ == "__main__":
    main()