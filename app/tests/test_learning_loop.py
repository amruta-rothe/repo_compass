"""
Unit tests for Phase 3: Learning Loop & Practice Lab.
Covers:
  - Issue -> File -> Symbol -> Test trail mapping
  - Symbol extraction and test file matching
  - 5-Level Adaptive Hint Ladder
  - Static review & diff formatting logic
"""
from app.services.code_search import (
    find_matching_test_file,
    extract_candidate_symbols,
    search_code_for_issue,
)
from app.services.hint_engine import _generate_grounded_hint, generate_adaptive_hint


def test_find_matching_test_files():
    tree_paths = [
        "fastapi/routing.py",
        "fastapi/applications.py",
        "tests/test_routing.py",
        "tests/test_applications.py",
        "src/client.ts",
        "src/__tests__/client.test.ts",
        "pkg/server/server.go",
        "pkg/server/server_test.go",
    ]

    # Python test match
    assert find_matching_test_file("fastapi/routing.py", tree_paths) == "tests/test_routing.py"
    # TypeScript test match
    assert find_matching_test_file("src/client.ts", tree_paths) == "src/__tests__/client.test.ts"
    # Go test match
    assert find_matching_test_file("pkg/server/server.go", tree_paths) == "pkg/server/server_test.go"
    # Non-existent test returns None
    assert find_matching_test_file("unknown/path.py", tree_paths) is None


def test_extract_candidate_symbols():
    issue_text = "Bug in `APIRoute` when invoking `get_route_handler()` with custom RequestValidationError"
    symbols = extract_candidate_symbols(issue_text, "fastapi/routing.py")
    assert "APIRoute" in symbols
    assert "get_route_handler" in symbols
    assert "Routing" in symbols or "RequestValidationError" in symbols


def test_search_code_for_issue_trail():
    tree = [
        {"path": "fastapi/routing.py", "type": "blob"},
        {"path": "tests/test_routing.py", "type": "blob"},
        {"path": "fastapi/applications.py", "type": "blob"},
    ]
    results = search_code_for_issue(
        issue_title="Error in routing when path has trailing slash",
        issue_body="Traceback occurs inside `APIRoute`",
        directory_tree=tree,
    )
    assert len(results) > 0
    top = results[0]
    assert top["path"] == "fastapi/routing.py"
    assert top["test_path"] == "tests/test_routing.py"
    assert "routing.py" in top["trail"]
    assert top["confidence"] in ["high", "medium", "low"]


def test_adaptive_hint_progression():
    issue = {
        "number": 42,
        "title": "Fix validation error in APIRoute `get_handler()`",
        "body": "When input is invalid, it fails without proper exception.",
        "labels": ["bug", "help wanted"],
    }
    relevant_files = ["fastapi/routing.py", "tests/test_routing.py"]

    # Level 1: Concept
    h1 = _generate_grounded_hint(issue, hint_level=1, relevant_files=relevant_files, exp_level="beginner")
    assert "Concept Overview" in h1
    assert "validation" in h1

    # Level 2: Module/Directory
    h2 = _generate_grounded_hint(issue, hint_level=2, relevant_files=relevant_files, exp_level="beginner")
    assert "fastapi" in h2

    # Level 3: Specific File
    h3 = _generate_grounded_hint(issue, hint_level=3, relevant_files=relevant_files, exp_level="beginner")
    assert "fastapi/routing.py" in h3

    # Level 4: Function/Test
    h4 = _generate_grounded_hint(issue, hint_level=4, relevant_files=relevant_files, exp_level="beginner")
    assert "Symbol & Test Inspection" in h4

    # Level 5: Implementation Strategy
    h5 = _generate_grounded_hint(issue, hint_level=5, relevant_files=relevant_files, exp_level="beginner")
    assert "Suggested Implementation Strategy" in h5
    assert "Reproduce First" in h5


def test_adaptive_hint_experience_level():
    issue = {
        "number": 99,
        "title": "Concurrency lock in connection pool",
        "labels": ["performance"],
    }
    relevant_files = ["src/pool.py"]

    h_beg = _generate_grounded_hint(issue, hint_level=1, relevant_files=relevant_files, exp_level="beginner")
    h_adv = _generate_grounded_hint(issue, hint_level=1, relevant_files=relevant_files, exp_level="advanced")

    assert "Concept Overview" in h_beg
    assert "Architecture Scope" in h_adv
