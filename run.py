# run.py
from __future__ import annotations

# macOS TLS fix: validate like curl (Keychain trust store)
try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

from app import main

if __name__ == "__main__":
    main()
