"""Unit tests verifying fixes for datetimes, detached instances, and Supabase integration."""
from datetime import datetime, timezone, timedelta
import types
import pytest

from app.services.repository_fetcher import _is_cache_valid, _as_utc
from app.services.issue_ranker import _days_stale
from app.core.supabase import get_supabase_client, get_supabase_admin_client, is_supabase_online
from app.db.session import get_db_info


def test_as_utc_and_cache_valid():
    now_naive = datetime.now()
    now_aware = _as_utc(now_naive)
    assert now_aware.tzinfo is not None

    future_naive = datetime.now() + timedelta(hours=3)
    snap = types.SimpleNamespace(expires_at=future_naive)
    assert _is_cache_valid(snap) is True

    past_aware = datetime.now(timezone.utc) - timedelta(hours=1)
    snap_past = types.SimpleNamespace(expires_at=past_aware)
    assert _is_cache_valid(snap_past) is False


def test_days_stale_robustness():
    # Naive datetime
    issue_naive = types.SimpleNamespace(updated_at_gh=datetime.now() - timedelta(days=7))
    stale = _days_stale(issue_naive)
    assert stale is not None and 6 <= stale <= 8

    # Aware datetime
    issue_aware = types.SimpleNamespace(updated_at_gh=datetime.now(timezone.utc) - timedelta(days=2))
    stale = _days_stale(issue_aware)
    assert stale is not None and 1 <= stale <= 3

    # String ISO format
    issue_str = types.SimpleNamespace(updated_at_gh="2026-09-01T00:00:00Z")
    stale = _days_stale(issue_str)
    assert stale is not None and stale > 10

    # None
    assert _days_stale(types.SimpleNamespace(updated_at_gh=None)) is None


def test_supabase_connectivity():
    client = get_supabase_client()
    assert client is not None
    admin = get_supabase_admin_client()
    assert admin is not None
    assert is_supabase_online() is True


def test_db_info():
    info = get_db_info()
    assert "type" in info
    assert "is_postgres" in info
