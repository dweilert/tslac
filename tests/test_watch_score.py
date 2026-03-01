from watch.score import score_page_against_topics, should_exclude


def test_should_exclude_querymark():
    assert should_exclude("https://example.com/a?b=1", ["?"]) is True
    assert should_exclude("https://example.com/a", ["?"]) is False

def test_score_prefers_earlier_topics():
    topics = ["grants", "digitization"]
    page = score_page_against_topics(
        url="u",
        title="Digitization efforts",
        meta="",
        body="This mentions grants once. grants.",
        topics=topics,
    )
    assert page is not None
    assert page["best_topic_index"] in (0, 1)
    assert "grants" in page["matched_topics"]
