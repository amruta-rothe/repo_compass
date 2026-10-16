"""
Unit tests for Maintainer Studio service (PRD Section 5.11).
"""
from app.services.maintainer_service import (
    analyze_issue_quality,
    classify_issue_maintainer,
    generate_grounded_improvement_draft,
    generate_grounded_starter_draft,
    find_related_issues_for_pr,
)


def test_analyze_issue_quality_complete():
    issue = {
        "title": "Bug in query router when header is empty",
        "body": """
        ## Steps to reproduce
        1. Call router with empty header.
        2. Expected 400 Bad Request, but got 500 internal error.
        
        ```python
        client.get('/items', headers={})
        ```
        
        Acceptance criteria:
        - Return HTTP 400 instead of 500
        """,
        "labels": ["bug"],
        "assignees": [],
    }
    quality = analyze_issue_quality(issue)
    assert quality["quality_score"] >= 80
    assert quality["checks"]["has_repro_steps"] is True
    assert quality["checks"]["has_expected_vs_actual"] is True
    assert quality["checks"]["has_logs_or_code"] is True
    assert quality["needs_more_info"] is False


def test_analyze_issue_quality_incomplete():
    issue = {
        "title": "Doesn't work",
        "body": "It fails on my machine",
        "labels": [],
        "assignees": [],
    }
    quality = analyze_issue_quality(issue)
    assert quality["quality_score"] < 45
    assert quality["needs_more_info"] is True
    assert "Missing detailed problem description" in quality["missing_items"]


def test_classify_issue_maintainer():
    good_issue = {
        "title": "Add helper method for parsing timestamps",
        "body": "Please add a utility function `parse_iso_timestamp` with tests and acceptance criteria.",
        "labels": ["good first issue"],
        "assignees": [],
    }
    bad_issue = {
        "title": "Broken",
        "body": "help",
        "labels": [],
        "assignees": [],
    }
    assert classify_issue_maintainer(good_issue, base_difficulty="beginner") in ["beginner", "intermediate"]
    assert classify_issue_maintainer(bad_issue, base_difficulty="beginner") == "needs-more-information"


def test_generate_drafts():
    issue = {
        "number": 105,
        "title": "Support WebP format in avatar uploads",
        "body": "Currently only JPEG and PNG are allowed.",
        "labels": ["feature"],
    }
    quality = analyze_issue_quality(issue)
    improvement = generate_grounded_improvement_draft(issue, quality)
    assert "[Clarified]" in improvement["improved_title"]
    assert "## Acceptance Criteria" in improvement["improved_body"]

    starter = generate_grounded_starter_draft(issue, likely_files=["app/images.py"])
    assert "good first issue" in starter["starter_title"]
    assert "app/images.py" in starter["starter_body"]


def test_find_related_issues_for_pr():
    issues = [
        {"number": 1, "title": "Refactor router.py handlers", "body": "Clean up routing.py"},
        {"number": 2, "title": "Fix memory leak in database.py", "body": "Connection pool issue"},
        {"number": 3, "title": "Update README docs", "body": "Add getting started"},
    ]
    changed_files = ["src/router.py", "src/routing.py"]
    related = find_related_issues_for_pr(changed_files, issues)
    assert len(related) > 0
    assert related[0]["number"] == 1
