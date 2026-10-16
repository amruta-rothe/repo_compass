"""
Unit tests for Phase 6: Safe Simulation & Isolated Runner (PRD Section 5.8).
"""
import pytest
from app.services.runner_service import (
    validate_patch_security,
    execute_patch_run,
)


def test_validate_patch_security_safe():
    safe_patch = """
    --- a/src/routing.py
    +++ b/src/routing.py
    @@ -10,3 +10,4 @@
     def my_function():
    +    return True
    """
    is_safe, err = validate_patch_security(safe_patch)
    assert is_safe is True
    assert err is None


def test_validate_patch_security_traversal_blocked():
    traversal_patch = """
    --- a/../../../etc/passwd
    +++ b/../../../etc/passwd
    @@ -1,1 +1,2 @@
    +evil:x:0:0:root:/root:/bin/bash
    """
    is_safe, err = validate_patch_security(traversal_patch)
    assert is_safe is False
    assert "Directory traversal is blocked" in err


def test_validate_patch_security_env_blocked():
    env_patch = """
    --- a/.env
    +++ b/.env
    @@ -1,1 +1,1 @@
    +SECRET=stolen
    """
    is_safe, err = validate_patch_security(env_patch)
    assert is_safe is False
    assert "Dangerous path detected" in err


def test_execute_patch_run_security_violation():
    bad_patch = "--- a/../../secret.txt\n+++ b/../../secret.txt\n"
    res = execute_patch_run(
        session_id="test_sess_sec",
        repo_full_name="org/repo",
        patch_content=bad_patch,
    )
    assert res["status"] == "failed"
    assert "Security Policy Violation" in res["output"]


def test_execute_patch_run_truthful_not_run_when_disabled():
    safe_patch = "--- a/src/math.py\n+++ b/src/math.py\n@@ -1 +1 @@\n+x = 1\n"
    res = execute_patch_run(
        session_id="test_sess_normal",
        repo_full_name="org/repo",
        patch_content=safe_patch,
        test_command="pytest",
    )
    assert res["status"] == "not_run"
    assert res["run_type"] == "static_review"
    assert "Tests Not Executed" in res["output"]
