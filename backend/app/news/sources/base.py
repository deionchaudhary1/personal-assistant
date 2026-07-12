"""Interface every news source adapter implements.

A source adapter is registered in ``app.news.registry.SOURCES``. The digest
service (``app.news.service``) polls each adapter's ``fetch()`` when its own
``SourceState.last_fetched_at`` is stale relative to ``refresh_interval`` —
each source keeps its own cadence rather than sharing one global fetch clock.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import Any, Dict, List


class SourceAdapter(ABC):
    """Protocol-ish base class: a name, a refresh cadence, and a fetch method."""

    name: str
    refresh_interval: timedelta

    @abstractmethod
    async def fetch(self) -> List[Dict[str, Any]]:
        """Return fresh items as ``{title, summary, url, published_date}`` dicts.

        Raises on network/parse failure — the caller (``app.news.service``)
        decides the fallback (serve stale cache), matching the
        never-break-the-page posture used elsewhere in the app.
        """
        raise NotImplementedError
