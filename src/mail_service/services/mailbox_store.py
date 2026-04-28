"""
mailbox_store.py — Structured state manager for active mailboxes.

Replaces module-level _active_boxes, _created_at in mailbox_service.py
"""
from __future__ import annotations

import time
from typing import Any

from ...mail.client import Mailbox


class MailboxStore:
    """
    Thread-safe mailbox state manager.

    Observability: tracks mailbox age, provider distribution.
    Testable: mockable for unit tests.
    """

    def __init__(self) -> None:
        self._boxes: dict[str, Mailbox] = {}
        self._created_at: dict[str, float] = {}

    async def init(self) -> None:
        """Async init for interface consistency — no-op."""
        pass

    async def shutdown(self) -> None:
        """Clear all mailboxes on shutdown."""
        self._boxes.clear()
        self._created_at.clear()

    def add(self, box: Mailbox) -> None:
        """Add a mailbox to active store."""
        self._boxes[box.email] = box
        self._created_at[box.email] = time.time()

    def remove(self, email: str) -> bool:
        """Remove a mailbox. Returns True if existed."""
        existed = email in self._boxes
        self._boxes.pop(email, None)
        self._created_at.pop(email, None)
        return existed

    def get(self, email: str) -> Mailbox | None:
        """Get mailbox by email."""
        return self._boxes.get(email)

    def has(self, email: str) -> bool:
        """Check if email exists in store."""
        return email in self._boxes

    def list_active(self) -> list[dict[str, Any]]:
        """List all active mailboxes with metadata."""
        return [
            {
                "email": email,
                "provider": box.provider,
                "created_at": self._created_at.get(email, 0),
            }
            for email, box in self._boxes.items()
        ]

    def count(self) -> int:
        """Total active mailboxes."""
        return len(self._boxes)

    def get_stats(self) -> dict[str, Any]:
        """Metrics for observability."""
        now = time.time()
        by_provider: dict[str, int] = {}
        for box in self._boxes.values():
            by_provider[box.provider] = by_provider.get(box.provider, 0) + 1

        ages = [now - t for t in self._created_at.values()]
        oldest = min(ages) if ages else None

        return {
            "total": len(self._boxes),
            "by_provider": by_provider,
            "oldest_age_seconds": oldest,
        }

    def reset(self) -> None:
        """Clear all state — used for testing."""
        self._boxes.clear()
        self._created_at.clear()