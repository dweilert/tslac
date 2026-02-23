#!/usr/bin/env python3ython

from __future__ import annotations

# macOS TLS fix: validate like curl (Keychain trust store)
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from http.server import HTTPServer

from config import HOST, PORT, OUT_DIR, STATE_DIR
from server import Handler

import http.server
import socketserver
import urllib.parse
import json
import yaml
import cleaner
import export_preview


def run_server():
    httpd = HTTPServer((HOST, PORT), Handler)
    print(f"Serving on http://{HOST}:{PORT}")
    print("Open that URL in a browser. Use 'Refresh candidates' to fetch latest.")
    httpd.serve_forever()


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    run_server()


if __name__ == "__main__":
    main()