"""
Tests for CircuitBreakerState.
"""
import pytest
from mail.circuit_breaker import CircuitBreakerState, CircuitBreakerConfig


@pytest.fixture
def cb():
    return CircuitBreakerState()


def test_init_shutdown(cb):
    """Test lifecycle methods."""
    import asyncio
    asyncio.run(cb.init())
    assert cb._fail_counts == {}
    asyncio.run(cb.shutdown())
    assert cb._fail_counts == {}


def test_is_down_initially_false(cb):
    """Test provider starts as available."""
    assert cb.is_down("testmail") is False


def test_mark_fail_triggers_cooldown(cb):
    """Test that max failures triggers cooldown."""
    config = CircuitBreakerConfig(max_consecutive_fails=3, cooldown_sec=60)
    cb = CircuitBreakerState(config)

    cb.mark_fail("testmail")
    assert cb.is_down("testmail") is False

    cb.mark_fail("testmail")
    cb.mark_fail("testmail")
    assert cb.is_down("testmail") is True


def test_mark_ok_clears_state(cb):
    """Test success clears failure count."""
    cb.mark_fail("testmail")
    assert "testmail" in cb._fail_counts

    cb.mark_ok("testmail")
    assert "testmail" not in cb._fail_counts


def test_get_stats(cb):
    """Test observability metrics."""
    cb.mark_fail("testmail")
    cb.mark_fail("mailtm")
    cb.mark_fail("mailtm")

    stats = cb.get_stats()
    assert stats["fail_counts"]["testmail"] == 1
    assert stats["fail_counts"]["mailtm"] == 2
    assert "config" in stats