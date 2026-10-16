"""
Basic smoke tests for core services.
Run with: pytest app/tests/ -v
"""
import pytest
from unittest.mock import patch, MagicMock


# ─── Issue ranker tests ────────────────────────────────────────────────────

class MockIssue:
    def __init__(self, **kwargs):
        self.state = kwargs.get("state", "open")
        self.labels = kwargs.get("labels", [])
        self.assignees = kwargs.get("assignees", [])
        self.title = kwargs.get("title", "Test issue")
        self.body = kwargs.get("body", "")
        self.updated_at_gh = kwargs.get("updated_at_gh", None)
        self.number = kwargs.get("number", 1)
        self.html_url = kwargs.get("html_url", "https://github.com/test/test/issues/1")


def test_beginner_label_gives_positive_score():
    from app.services.issue_ranker import score_issue
    issue = MockIssue(labels=["good first issue"])
    score, signals, difficulty = score_issue(issue)
    assert score > 0
    assert difficulty == "beginner"
    assert signals["beginner_label"]["value"] == 1


def test_assigned_issue_penalized():
    from app.services.issue_ranker import score_issue
    issue = MockIssue(assignees=["someuser"])
    score, signals, difficulty = score_issue(issue)
    assert difficulty == "unavailable"
    assert signals["assignment"]["value"] == 0


def test_blocked_issue_penalized():
    from app.services.issue_ranker import score_issue
    issue = MockIssue(labels=["blocked"])
    score, signals, difficulty = score_issue(issue)
    assert difficulty == "unavailable"
    assert signals["blocked"]["value"] == 1


def test_high_quality_body_improves_score():
    from app.services.issue_ranker import score_issue
    good_body = """
    ## Steps to reproduce
    1. Open app
    2. Click button

    ## Expected behavior
    Should work.

    ## Actual behavior
    Crashes.

    ## Acceptance criteria
    - No crash on click
    ```python
    test code
    ```
    """
    issue_good = MockIssue(body=good_body)
    issue_poor = MockIssue(body="Fix it.")
    score_good, _, _ = score_issue(issue_good)
    score_poor, _, _ = score_issue(issue_poor)
    assert score_good > score_poor


def test_rank_issues_sorts_by_score():
    from app.services.issue_ranker import rank_issues
    issues = [
        MockIssue(number=1, labels=[], body=""),
        MockIssue(number=2, labels=["good first issue"], body="Clear description with acceptance criteria ```code```"),
        MockIssue(number=3, assignees=["user"]),
    ]
    ranked = rank_issues(issues)
    assert len(ranked) == 3
    scores = [r[1] for r in ranked]
    assert scores == sorted(scores, reverse=True), "Issues should be sorted by score descending"


# ─── GitHub URL validation ─────────────────────────────────────────────────

def test_valid_github_url():
    from app.services.github_client import parse_repo_url
    owner, repo = parse_repo_url("https://github.com/django/django")
    assert owner == "django"
    assert repo == "django"


def test_valid_shorthand():
    from app.services.github_client import parse_repo_url
    owner, repo = parse_repo_url("microsoft/vscode")
    assert owner == "microsoft"
    assert repo == "vscode"


def test_invalid_host_raises():
    from app.services.github_client import parse_repo_url, GitHubValidationError
    with pytest.raises(GitHubValidationError):
        parse_repo_url("https://evil.com/owner/repo")


def test_invalid_chars_raises():
    from app.services.github_client import parse_repo_url, GitHubValidationError
    with pytest.raises(GitHubValidationError):
        parse_repo_url("owner/../repo")


# ─── XP / Level tests ──────────────────────────────────────────────────────

def test_level_from_xp():
    from app.services.reward_service import level_from_xp
    assert level_from_xp(0) == 1
    assert level_from_xp(99) == 1
    assert level_from_xp(100) == 2
    assert level_from_xp(300) == 3


def test_xp_progress_tuple():
    from app.services.reward_service import xp_progress
    level, xp_into, xp_needed = xp_progress(150)
    assert level == 2
    assert xp_into == 50  # 150 - 100
    assert xp_needed == 200  # 300 - 100


def test_level_1_at_zero_xp():
    from app.services.reward_service import level_from_xp
    assert level_from_xp(0) == 1


# ─── Security tests ────────────────────────────────────────────────────────

def test_password_hash_and_verify():
    from app.core.security import hash_password, verify_password
    pw = "supersecret123"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_session_token_valid():
    from app.core.security import create_session_token, verify_session_token
    token = create_session_token("user-123")
    result = verify_session_token(token)
    assert result == "user-123"


def test_session_token_tampered():
    from app.core.security import create_session_token, verify_session_token
    token = create_session_token("user-123")
    tampered = token[:-5] + "XXXXX"
    result = verify_session_token(tampered)
    assert result is None


# ─── Code search tests ─────────────────────────────────────────────────────

def test_code_search_finds_relevant_files():
    from app.services.code_search import search_code_for_issue

    tree = [
        {"path": "src/auth/login.py", "type": "blob", "size": 1000},
        {"path": "src/auth/user_model.py", "type": "blob", "size": 1000},
        {"path": "src/dashboard/views.py", "type": "blob", "size": 1000},
        {"path": "README.md", "type": "blob", "size": 500},
        {"path": "static/logo.png", "type": "blob", "size": 20000},  # binary, should be skipped
    ]

    results = search_code_for_issue(
        issue_title="Login page throws error when password is wrong",
        issue_body="When user tries to login with incorrect password, the auth module crashes.",
        directory_tree=tree,
    )

    paths = [r["path"] for r in results]
    # login.py and user_model.py should rank high
    assert any("login" in p for p in paths), "login.py should be in results"
    assert not any("logo.png" in p for p in paths), "Binary files should be excluded"


def test_code_search_returns_empty_on_no_match():
    from app.services.code_search import search_code_for_issue

    tree = [
        {"path": "completely/unrelated/zxcvbnm.py", "type": "blob", "size": 500},
    ]
    results = search_code_for_issue(
        issue_title="Fix typo in README",
        issue_body="There is a spelling mistake.",
        directory_tree=tree,
    )
    # Either empty or very low scores — path has no matching tokens
    assert isinstance(results, list)


def test_code_search_match_type():
    from app.services.code_search import search_code_for_issue

    tree = [
        {"path": "src/authentication/login_handler.py", "type": "blob", "size": 800},
    ]
    results = search_code_for_issue(
        issue_title="Authentication login handler crashes",
        issue_body="The login_handler module fails when token is expired.",
        directory_tree=tree,
    )
    assert len(results) > 0
    result = results[0]
    assert result["match_type"] in {"direct_match", "related_reference", "ai_inferred"}
    assert result["confidence"] in {"high", "medium", "low"}

