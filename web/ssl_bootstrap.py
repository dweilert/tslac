# web/ssl_bootstrap.py
def setup_tls_truststore() -> None:
    try:
        import truststore

        truststore.inject_into_ssl()
    except Exception:
        pass
