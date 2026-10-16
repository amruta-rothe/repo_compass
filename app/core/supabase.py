"""
Supabase client provider for RepoCompass.
Manages both client-side (anon) and server-side (service_role) Supabase clients.
"""
from __future__ import annotations

import logging
from typing import Optional
from supabase import create_client, Client

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


def get_supabase_client() -> Optional[Client]:
    """Get or create the standard Supabase client (using anon key)."""
    global _supabase_client
    settings = get_settings()

    if not settings.supabase_configured:
        return None

    if _supabase_client is None:
        try:
            _supabase_client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=settings.supabase_anon_key,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            return None

    return _supabase_client


def get_supabase_admin_client() -> Optional[Client]:
    """
    Get or create the administrative Supabase client (using service_role key).
    Required for programmatic user management without user confirmation emails.
    """
    global _supabase_admin_client
    settings = get_settings()

    if not settings.supabase_url:
        return None

    admin_key = settings.supabase_service_role_key or settings.supabase_anon_key
    if not admin_key:
        return None

    if _supabase_admin_client is None:
        try:
            _supabase_admin_client = create_client(
                supabase_url=settings.supabase_url,
                supabase_key=admin_key,
            )
        except Exception as e:
            logger.error(f"Failed to initialize Supabase admin client: {e}")
            return None

    return _supabase_admin_client


def is_supabase_online() -> bool:
    """Test if the Supabase project is reachable and credentials are valid."""
    admin = get_supabase_admin_client()
    if not admin:
        return False
    try:
        admin.auth.admin.list_users()
        return True
    except Exception as e:
        logger.warning(f"Supabase ping check failed: {e}")
        return False
