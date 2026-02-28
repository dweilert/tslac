from pathlib import Path

from collect.parse_homepage import parse_homepage_candidates

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def test_parse_homepage_candidates_smoke():
    html = load_fixture("homepage.html")

    items = parse_homepage_candidates(
        html,
        base_url="https://www.tsl.texas.gov/",
    )

    # Parser should find real homepage stories
    assert len(items) >= 3

    # Ensure we captured actual article nodes
    assert any("/node/" in c.url for c in items)
