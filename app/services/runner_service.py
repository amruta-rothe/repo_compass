"""
Isolated Runner Service for RepoCompass (PRD Section 5.8 & Phase 6).
Handles:
  1. Patch path traversal security validation (anti-SSRF / path escape)
  2. Isolated test runner client (when RUNNER_ENABLED=true)
  3. Truthful execution status reporting (not_run, running, passed, failed, unavailable)
  4. Untrusted output escaping and PracticeRun persistence
  5. Security boundary enforcement (never runs untrusted repo code on host)
"""
from __future__ import annotations

import re
import html
import httpx
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import PracticeSession, PracticeRun
from app.services.reward_service import award_xp


class SecurityViolationError(Exception):
    """Raised when a patch attempts path traversal or malicious path manipulation."""
    pass


def validate_patch_security(patch_content: str) -> Tuple[bool, Optional[str]]:
    """
    Validates patch against directory traversal and dangerous paths.
    Returns (is_safe, error_message).
    """
    if not patch_content or not patch_content.strip():
        return True, None

    dangerous_patterns = [
        r'\.\.[/\\]',                # Traversal: ../ or ..\
        r'^[/\\]',                   # Absolute path starting with root slash
        r'^[a-zA-Z]:[/\\]',          # Windows drive path C:\
        r'/etc/',                    # Unix system paths
        r'/var/',
        r'/proc/',
        r'/sys/',
        r'\.git[/\\]',               # Modifying .git internal metadata
        r'\.env',                    # Targeting environment credentials
    ]

    for line in patch_content.splitlines():
        line_clean = line.strip()
        if line_clean.startswith("---") or line_clean.startswith("+++"):
            parts = line_clean.split(maxsplit=1)
            if len(parts) > 1:
                path = parts[1].strip()
                # Strip leading a/ or b/ from git diff
                if path.startswith("a/") or path.startswith("b/"):
                    path = path[2:]

                for pattern in dangerous_patterns:
                    if re.search(pattern, path, re.IGNORECASE):
                        return False, f"Dangerous path detected in patch: '{path}'. Directory traversal is blocked."

    return True, None


def execute_patch_run(
    session_id: str,
    repo_full_name: str,
    patch_content: str,
    test_command: str = "pytest",
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Executes or simulates a patch test run within strict security boundaries.
    If isolated runner is disabled, records status truthfully as 'not_run'.
    """
    settings = get_settings()

    # 1. Security Check
    is_safe, sec_err = validate_patch_security(patch_content)
    if not is_safe:
        return {
            "status": "failed",
            "run_type": "security_check",
            "output": f"Security Policy Violation: {sec_err}",
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

    # 2. Check if external runner is configured
    if settings.runner_enabled and settings.runner_base_url:
        headers = {}
        if settings.runner_api_key:
            headers["Authorization"] = f"Bearer {settings.runner_api_key}"

        payload = {
            "repository": repo_full_name,
            "patch": patch_content,
            "command": test_command,
            "timeout": settings.runner_timeout_seconds,
        }

        try:
            resp = httpx.post(
                f"{settings.runner_base_url.rstrip('/')}/api/runs",
                json=payload,
                headers=headers,
                timeout=float(settings.runner_timeout_seconds + 5),
            )
            data = resp.json()
            run_status = data.get("status", "failed")
            raw_output = data.get("output", "")
            safe_output = html.escape(raw_output)

            # Persist to PracticeRun
            _record_practice_run(
                session_id=session_id,
                run_type="isolated_run",
                status=run_status,
                output=safe_output,
            )

            if run_status == "passed" and user_id:
                award_xp(user_id, "test_passed", idempotency_context=f"run_{session_id}")

            return {
                "status": run_status,
                "run_type": "isolated_run",
                "output": safe_output,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            safe_err = html.escape(str(e))
            _record_practice_run(
                session_id=session_id,
                run_type="isolated_run",
                status="unavailable",
                output=f"Isolated runner unavailable: {safe_err}",
            )
            return {
                "status": "unavailable",
                "run_type": "isolated_run",
                "output": f"Isolated runner service unavailable: {safe_err}",
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }

    # 3. Safe Static Review Mode (Runner Disabled)
    safe_notice = (
        "Tests Not Executed (Static Review Mode)\n"
        "Security Boundary Policy: Main application server does not execute untrusted repository code.\n"
        "To run tests, clone the repository locally and run:\n"
        f"  $ {test_command}\n"
    )
    _record_practice_run(
        session_id=session_id,
        run_type="static_review",
        status="not_run",
        output=safe_notice,
    )

    return {
        "status": "not_run",
        "run_type": "static_review",
        "output": safe_notice,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def _record_practice_run(session_id: str, run_type: str, status: str, output: str):
    """Saves PracticeRun entity to database."""
    try:
        with get_db() as session:
            run = PracticeRun(
                id=str(uuid.uuid4()),
                session_id=session_id,
                run_type=run_type,
                status=status,
                output=output[:10000],  # bounded output
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            session.add(run)
    except Exception:
        pass


def get_latest_run(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves the latest PracticeRun record for a session."""
    try:
        with get_db() as session:
            run = (
                session.query(PracticeRun)
                .filter_by(session_id=session_id)
                .order_by(PracticeRun.started_at.desc())
                .first()
            )
            if run:
                return {
                    "id": run.id,
                    "status": run.status,
                    "run_type": run.run_type,
                    "output": run.output,
                    "started_at": run.started_at,
                    "completed_at": run.completed_at,
                }
    except Exception:
        pass
    return None
