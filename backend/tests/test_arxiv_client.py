"""Tests for app/news/sources/arxiv.py's pure parsing/truncation functions.

No network access — parse_feed is exercised against a hand-written Atom XML
fixture with realistic namespace/structure.
"""

from __future__ import annotations

from datetime import date

from app.news.sources.arxiv import _truncate_summary, parse_feed

FIXTURE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>ArXiv Query</title>
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <updated>2024-01-15T18:00:00Z</updated>
    <published>2024-01-15T18:00:00Z</published>
    <title>A Great Paper About
   Language Models</title>
    <summary>  This paper introduces a new method for training language
models. It achieves state-of-the-art results on several benchmarks.
We release code and weights.
    </summary>
    <link href="http://arxiv.org/abs/2401.00001v1" rel="alternate" type="text/html"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.00002v2</id>
    <updated>2024-01-14T12:30:00Z</updated>
    <published>2024-01-14T12:30:00Z</published>
    <title>Scaling Reinforcement Learning</title>
    <summary>We present a very long abstract that goes on and on without an early sentence break of any kind so that it will certainly exceed the two hundred character truncation limit that the digest imposes on every single summary field regardless of content length or structure.</summary>
    <link href="http://arxiv.org/abs/2401.00002v2" rel="alternate" type="text/html"/>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.00003v1</id>
    <updated>2024-01-13T09:00:00Z</updated>
    <published>2024-01-13T09:00:00Z</published>
    <title>Short Abstract Paper</title>
    <summary>Short abstract.</summary>
    <link href="http://arxiv.org/abs/2401.00003v1" rel="alternate" type="text/html"/>
  </entry>
</feed>
"""


def test_parse_feed_extracts_all_entries():
    items = parse_feed(FIXTURE_XML)
    assert len(items) == 3


def test_parse_feed_field_extraction():
    items = parse_feed(FIXTURE_XML)
    third = items[2]
    assert third["title"] == "Short Abstract Paper"
    assert third["url"] == "http://arxiv.org/abs/2401.00003v1"
    assert third["published_date"] == date(2024, 1, 13)
    assert third["summary"] == "Short abstract."


def test_parse_feed_collapses_newlines_in_title_and_summary():
    items = parse_feed(FIXTURE_XML)
    first = items[0]
    assert "\n" not in first["title"]
    assert first["title"] == "A Great Paper About Language Models"
    assert "\n" not in first["summary"]


def test_parse_feed_truncates_to_first_sentence_when_short_enough():
    items = parse_feed(FIXTURE_XML)
    first = items[0]
    assert first["summary"] == (
        "This paper introduces a new method for training language models."
    )


def test_parse_feed_truncates_to_200_chars_when_no_early_sentence_break():
    items = parse_feed(FIXTURE_XML)
    second = items[1]
    assert second["summary"].endswith("…")
    # 200 chars of body + the appended ellipsis character.
    assert len(second["summary"]) == 201


def test_truncate_summary_collapses_whitespace():
    raw = "Line one\nLine two\n   Line three."
    assert _truncate_summary(raw) == "Line one Line two Line three."


def test_truncate_summary_first_sentence():
    raw = "First sentence here. Second sentence that would be dropped."
    assert _truncate_summary(raw) == "First sentence here."


def test_truncate_summary_hard_limit_with_ellipsis():
    raw = "word " * 100  # no sentence terminator, far over 200 chars
    result = _truncate_summary(raw)
    assert result.endswith("…")
    assert len(result) <= 201
    assert len(result) > 190
