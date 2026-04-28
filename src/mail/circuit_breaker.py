"""
circuit_breaker.py — Structured state manager for mail provider circuit breaker.

Replaces module-level _provider_fail_counts, _provider_cooldown_until
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

LogFn = Callable[[str], None]


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    cooldown_sec: int = 120
    max_consecutive_fails: int = 3


class CircuitBreakerState:
    """
    Manages provider fail counts and cooldown state.

    Thread-safe for async use (single-threaded asyncio).
    Observable — exposes metrics for monitoring.
    """

    def __init__(self, config: CircuitBreakerConfig | None = None) -> None:
        self._config = config or CircuitBreakerConfig()
        self._fail_counts: dict[str, int] = {}
        self._cooldown_until: dict[str, float] = {}

    async def init(self) -> None:
        """Async init for interface consistency — no-op for sync state."""
        pass

    async def shutdown(self) -> None:
        """Clear state on shutdown."""
        self._fail_counts.clear()
        self._cooldown_until.clear()

    def is_down(self, provider: str) -> bool:
        """Check if provider is in cooldown."""
        deadline = self._cooldown_until.get(provider)
        if deadline is None:
            return False
        if time.monotonic() >= deadline:
            self._fail_counts.pop(provider, None)
            self._cooldown_until.pop(provider, None)
            return False
        return True

    def mark_fail(self, provider: str, log_fn: LogFn | None = None) -> bool:
        """
        Record a failure. Returns True if cooldown triggered.
        """
        count = self._fail_counts.get(provider, 0) + 1
        self._fail_counts[provider] = count
        triggered = count >= self._config.max_consecutive_fails
        if triggered:
            self._cooldown_until[provider] = time.monotonic() + self._config.cooldown_sec
        if log_fn:
            if triggered:
                log_fn(f"  [mail] {provider} fail {count} times -> cooldown {self._config.cooldown_sec}s")
            else:
                log_fn(f"  [mail] {provider} fail {count}/{self._config.max_consecutive_fails}")
        return triggered

    def mark_ok(self, provider: str) -> None:
        """Clear failure state on success."""
        self._fail_counts.pop(provider, None)
        self._cooldown_until.pop(provider, None)

    def get_stats(self) -> dict[str, Any]:
        """
        Metrics for observability.

        Returns:
            {
                "fail_counts": {"provider": count},
                "cooldown_providers": ["provider1", "provider2"],
                "config": {"cooldown_sec": 120, "max_consecutive_fails": 3}
            }
        """
        return {
            "fail_counts": dict(self._fail_counts),
            "cooldown_providers": [
                p for p, d in self._cooldown_until.items()
                if time.monotonic() < d
            ],
            "config": {
                "cooldown_sec": self._config.cooldown_sec,
                "max_consecutive_fails": self._config.max_consecutive_fails,
            },
        }

    def reset(self) -> None:
        """Clear all state — used for testing."""
        self._fail_counts.clear()
        self._cooldown_until.clear()