"""
GitHub REST API client with rate-limit handling, caching and SSRF protection.
Never executes repository code. Treats all repository content as untrusted.
"""
from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings


# ─── URL validation ────────────────────────────────────────────────────────

_GITHUB_HOST = "github.com"
_GITHUB_API = "https://api.github.com"
_REPO_RE = re.compile(r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$")


class GitHubValidationError(Exception):
    pass


class GitHubRateLimitError(Exception):
    pass


class GitHubNotFoundError(Exception):
    pass


def parse_repo_url(input_str: str) -> Tuple[str, str]:
    """
    Accept 'owner/repo' or 'https://github.com/owner/repo[...]'.
    Returns (owner, repo) or raises GitHubValidationError.
    """
    s = input_str.strip().rstrip("/")

    if "/" not in s:
        raise GitHubValidationError("Please enter owner/repo or a full GitHub URL.")

    # Full URL
    if s.startswith("http"):
        parsed = urlparse(s)
        if parsed.hostname not in (_GITHUB_HOST, f"www.{_GITHUB_HOST}"):
            raise GitHubValidationError(
                "Only github.com repositories are supported to prevent SSRF."
            )
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2:
            raise GitHubValidationError("Could not extract owner/repo from URL.")
        owner, repo = parts[0], parts[1]
    else:
        parts = s.split("/")
        if len(parts) != 2:
            raise GitHubValidationError("Expected format: owner/repo")
        owner, repo = parts[0], parts[1]

    # Sanitize
    if not re.match(r"^[A-Za-z0-9_.\-]+$", owner) or not re.match(r"^[A-Za-z0-9_.\-]+$", repo):
        raise GitHubValidationError("Repository name contains invalid characters.")

    return owner, repo


# ─── HTTP client ───────────────────────────────────────────────────────────

def _make_headers() -> Dict[str, str]:
    settings = get_settings()
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


def _handle_response(resp: httpx.Response, url: str) -> Dict:
    if resp.status_code == 403 and "rate limit" in resp.text.lower():
        reset = resp.headers.get("X-RateLimit-Reset", "unknown")
        raise GitHubRateLimitError(
            f"GitHub rate limit exceeded. Resets at: {reset}"
        )
    if resp.status_code == 404:
        raise GitHubNotFoundError(f"Not found: {url}")
    resp.raise_for_status()
    return resp.json()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(httpx.HTTPError),
    reraise=True,
)
def _get(path: str, params: Optional[Dict] = None) -> Any:
    url = f"{_GITHUB_API}{path}"
    with httpx.Client(timeout=20.0) as client:
        resp = client.get(url, headers=_make_headers(), params=params or {})
    return _handle_response(resp, url)


# ─── Repository data fetchers ──────────────────────────────────────────────

def fetch_repo_metadata(owner: str, repo: str) -> Dict:
    """Fetch basic repository metadata."""
    return _get(f"/repos/{owner}/{repo}")


def fetch_readme(owner: str, repo: str) -> Optional[str]:
    """Fetch decoded README content. Returns None if not found."""
    import base64
    try:
        data = _get(f"/repos/{owner}/{repo}/readme")
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content")
    except GitHubNotFoundError:
        return None


def fetch_file_content(owner: str, repo: str, path: str) -> Optional[str]:
    """Fetch decoded content of a specific file. Returns None if not found."""
    import base64
    settings = get_settings()
    try:
        data = _get(f"/repos/{owner}/{repo}/contents/{path}")
        if isinstance(data, list):
            return None  # It's a directory
        size = data.get("size", 0)
        if size > settings.max_source_file_bytes:
            return f"[File too large: {size} bytes — truncated for safety]"
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content")
    except (GitHubNotFoundError, Exception):
        return None


def fetch_directory_tree(owner: str, repo: str, max_files: int = 500) -> List[Dict]:
    """
    Fetch the repository file tree (truncated to max_files).
    Returns [{path, type, size}].
    """
    try:
        data = _get(f"/repos/{owner}/{repo}/git/trees/HEAD", params={"recursive": "1"})
        tree = data.get("tree", [])
        result = []
        for item in tree[:max_files]:
            result.append({
                "path": item.get("path", ""),
                "type": item.get("type", "blob"),
                "size": item.get("size", 0),
            })
        return result
    except Exception:
        return []


def fetch_open_issues(owner: str, repo: str, per_page: int = 50) -> List[Dict]:
    """Fetch open issues (excludes pull requests)."""
    issues = []
    page = 1
    while len(issues) < per_page:
        batch = _get(
            f"/repos/{owner}/{repo}/issues",
            params={"state": "open", "per_page": min(per_page, 100), "page": page},
        )
        if not batch:
            break
        for item in batch:
            if "pull_request" not in item:  # exclude PRs from issue list
                issues.append(item)
        if len(batch) < 100:
            break
        page += 1

    return issues[:per_page]


def fetch_labels(owner: str, repo: str) -> List[Dict]:
    try:
        return _get(f"/repos/{owner}/{repo}/labels", params={"per_page": 100})
    except Exception:
        return []


def fetch_recent_commits(owner: str, repo: str, n: int = 20) -> List[Dict]:
    try:
        return _get(f"/repos/{owner}/{repo}/commits", params={"per_page": n})
    except Exception:
        return []


def fetch_contributing(owner: str, repo: str) -> Optional[str]:
    """Try common contributing file names."""
    for path in ["CONTRIBUTING.md", "CONTRIBUTING.rst", "CONTRIBUTING.txt", "docs/CONTRIBUTING.md"]:
        content = fetch_file_content(owner, repo, path)
        if content:
            return content
    return None


def fetch_dependency_files(owner: str, repo: str) -> Dict[str, str]:
    """Fetch common dependency/config files."""
    candidates = [
        "package.json", "requirements.txt", "pyproject.toml", "setup.py",
        "Cargo.toml", "go.mod", "pom.xml", "build.gradle", "Gemfile",
        "composer.json", "pubspec.yaml", "CMakeLists.txt",
        "Makefile", "Dockerfile", ".github/workflows",
    ]
    result = {}
    for path in candidates:
        content = fetch_file_content(owner, repo, path)
        if content:
            result[path] = content[:5000]  # cap per-file
    return result
