"""RAG step: pick the best current signal for a topic from the intake-spine store."""
import os

import intake_core.store as store


def select_signal(query: str, db_path: str) -> dict | None:
    """Return the most recent signal whose topic matches `query`, or None.

    Shape: {"id","media_item_id","topic","entities":list,"summary"}.
    `get_signals` already orders most-recent-first and LIKE-matches the topic.
    A missing store file is treated as "no signals yet" rather than an error.
    """
    if not os.path.exists(db_path):
        return None
    rows = store.get_signals(db_path, topic=query, limit=1)
    return rows[0] if rows else None
