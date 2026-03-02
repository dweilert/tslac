from __future__ import annotations

import services.api_service as svc
from web.errors import BadRequestError


def test_clean_article_payload_rejects_missing_url():
    try:
        svc.clean_article_payload("")
    except BadRequestError:
        pass
    else:
        raise AssertionError("expected BadRequestError")


def test_clean_article_payload_parses_title_html_and_images():
    def fake_fetch(_url: str) -> str:
        return """
        <html>
          <head>
            <title>Hello World</title>
            <meta property="og:image" content="https://example.com/hero.png"/>
          </head>
          <body>
            <main>
              <h1>Headline</h1>
              <p>Para 1</p>
              <p>Para 2</p>
              <img src="/img/a.png" alt="A" width="800" height="400"/>
              <img src="/img/b.png" alt="B"/>
            </main>
            <footer>noise</footer>
          </body>
        </html>
        """

    payload = svc.clean_article_payload("https://site.test/page", fetch_html=fake_fetch)

    assert payload["title"] == "Hello World"
    assert isinstance(payload["html"], str)
    assert "<p>" in payload["html"]  # cleaned html has paragraphs
    assert isinstance(payload["images"], list)
    assert payload["images"]  # at least one image

    # og:image should appear and is usually top-ranked
    assert payload["images"][0]["src"] == "https://example.com/hero.png"


def test_clean_article_payload_image_urls_are_absolute():
    def fake_fetch(_url: str) -> str:
        return """
        <html>
          <head><title>T</title></head>
          <body>
            <main>
              <p>x</p>
              <img src="/img/a.png" alt="A"/>
            </main>
          </body>
        </html>
        """

    payload = svc.clean_article_payload("https://site.test/page", fetch_html=fake_fetch)
    # the extracted image should be absolute (joined with base)
    assert payload["images"][0]["src"].startswith("https://")
