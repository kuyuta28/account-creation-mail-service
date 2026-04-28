"""
Tests for MailboxStore.
"""
import pytest
import time
from mail.client import Mailbox
from mail_service.services.mailbox_store import MailboxStore


@pytest.fixture
def store():
    return MailboxStore()


@pytest.fixture
def sample_mailbox():
    return Mailbox(
        email="test@example.com",
        token="token123",
        account_id="acc123",
        base_url="https://api.mail.tm",
        provider="mail.tm",
    )


def test_add_and_get(store, sample_mailbox):
    """Test basic add/get."""
    store.add(sample_mailbox)
    assert store.get("test@example.com") == sample_mailbox


def test_remove(store, sample_mailbox):
    """Test remove returns True and clears."""
    store.add(sample_mailbox)
    assert store.remove("test@example.com") is True
    assert store.get("test@example.com") is None


def test_remove_nonexistent(store):
    """Test remove returns False for nonexistent."""
    assert store.remove("nonexistent@example.com") is False


def test_list_active(store, sample_mailbox):
    """Test listing active mailboxes."""
    store.add(sample_mailbox)
    result = store.list_active()
    assert len(result) == 1
    assert result[0]["email"] == "test@example.com"


def test_count(store, sample_mailbox):
    """Test count."""
    assert store.count() == 0
    store.add(sample_mailbox)
    assert store.count() == 1


def test_get_stats(store, sample_mailbox):
    """Test observability metrics."""
    store.add(sample_mailbox)
    time.sleep(0.01)

    stats = store.get_stats()
    assert stats["total"] == 1
    assert stats["by_provider"]["mail.tm"] == 1
    assert stats["oldest_age_seconds"] is not None