"""The list of registered news source adapters.

Adding a source means dropping a new file in app/news/sources/ implementing
the SourceAdapter interface (app/news/sources/base.py) and appending it here.
"""

from __future__ import annotations

from typing import List

from app.news.sources.arxiv import ArxivSource
from app.news.sources.base import SourceAdapter
from app.news.sources.hackernews import HackerNewsSource
from app.news.sources.rss import RssSource

SOURCES: List[SourceAdapter] = [ArxivSource(), HackerNewsSource(), RssSource()]
