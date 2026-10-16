"""
Repository fetcher — orchestrates GitHub API calls into a RepositorySnapshot.
Uses SQLAlchemy for persistence and respects cache TTL.
Returns plain dicts (not ORM objects) to avoid DetachedInstanceError.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Repository, RepositorySnapshot, Issue, IssueScore
from app.db.session import get_db
from app.services import github_client as gh
from app.services.github_client import GitHubValidationError, GitHubRateLimitError, GitHubNotFoundError


CACHE_TTL_HOURS = 4


class FetchError(Exception):
    pass


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_cache_valid(snapshot: RepositorySnapshot) -> bool:
    if not snapshot or not snapshot.expires_at:
        return False
    expires_at = _as_utc(snapshot.expires_at)
    return datetime.now(timezone.utc) < expires_at


def get_or_create_repository(owner: str, repo_name: str, session: Session) -> Repository:
    full_name = f"{owner}/{repo_name}"
    repo = session.query(Repository).filter_by(full_name=full_name).first()
    if not repo:
        repo = Repository(
            id=str(uuid.uuid4()),
            owner=owner,
            name=repo_name,
            full_name=full_name,
            url=f"https://github.com/{full_name}",
        )
        session.add(repo)
        session.flush()
    return repo


def _repo_to_dict(repo: Repository) -> dict:
    """Convert Repository ORM object to plain dict while still in session."""
    return {
        "id": repo.id,
        "owner": repo.owner,
        "name": repo.name,
        "full_name": repo.full_name,
        "url": repo.url,
        "description": repo.description,
        "primary_language": repo.primary_language,
        "topics": repo.topics or [],
        "stars": repo.stars or 0,
        "open_issues_count": repo.open_issues_count or 0,
        "analysis_status": repo.analysis_status,
        "last_analyzed_at": repo.last_analyzed_at,
    }


def _snapshot_to_dict(snapshot: Optional[RepositorySnapshot]) -> Optional[dict]:
    """Convert RepositorySnapshot ORM object to plain dict."""
    if not snapshot:
        return None
    return {
        "id": snapshot.id,
        "sha": snapshot.sha,
        "raw_data": snapshot.raw_data or {},
        "directory_tree": snapshot.directory_tree or [],
        "readme_content": snapshot.readme_content,
        "contributing_content": snapshot.contributing_content,
        "dependency_files": snapshot.dependency_files or {},
        "fetched_at": snapshot.fetched_at,
        "expires_at": snapshot.expires_at,
    }


def _issue_to_dict(issue: Issue) -> dict:
    """Convert Issue ORM object to plain dict."""
    return {
        "id": issue.id,
        "github_id": issue.github_id,
        "number": issue.number,
        "title": issue.title,
        "body": issue.body,
        "state": issue.state,
        "labels": issue.labels or [],
        "assignees": issue.assignees or [],
        "author": issue.author,
        "html_url": issue.html_url,
        "comments_count": issue.comments_count or 0,
        "created_at_gh": issue.created_at_gh,
        "updated_at_gh": issue.updated_at_gh,
    }


def fetch_and_cache_repository(
    input_str: str,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Main entry point. Accepts URL or 'owner/repo'.
    Returns a dict with repo metadata, snapshot, issues etc. — all as plain dicts.
    Raises FetchError on unrecoverable errors.
    """
    settings = get_settings()

    try:
        owner, repo_name = gh.parse_repo_url(input_str)
    except GitHubValidationError as e:
        raise FetchError(str(e))

    with get_db() as session:
        repo = get_or_create_repository(owner, repo_name, session)

        # Check cache
        latest_snapshot = (
            session.query(RepositorySnapshot)
            .filter_by(repository_id=repo.id)
            .order_by(RepositorySnapshot.fetched_at.desc())
            .first()
        )

        if not force_refresh and _is_cache_valid(latest_snapshot):
            # Return cached data — convert to dicts while session is open
            issues = session.query(Issue).filter_by(repository_id=repo.id, state="open").all()
            return _build_result(repo, latest_snapshot, issues, from_cache=True)

        # Mark repo as running
        repo.analysis_status = "running"
        session.flush()

        errors = {}

        # ── Fetch metadata ────────────────────────────────────────────────
        try:
            meta = gh.fetch_repo_metadata(owner, repo_name)
            repo.description = meta.get("description", "")
            repo.primary_language = meta.get("language")
            repo.topics = meta.get("topics", [])
            repo.stars = meta.get("stargazers_count", 0)
            repo.open_issues_count = meta.get("open_issues_count", 0)
        except GitHubRateLimitError as e:
            raise FetchError(str(e))
        except GitHubNotFoundError:
            raise FetchError(f"Repository '{owner}/{repo_name}' not found on GitHub.")
        except Exception as e:
            raise FetchError(f"Failed to fetch repository metadata: {e}")

        # ── Fetch content ─────────────────────────────────────────────────
        readme = None
        try:
            readme = gh.fetch_readme(owner, repo_name)
        except Exception as e:
            errors["readme"] = str(e)

        contributing = None
        try:
            contributing = gh.fetch_contributing(owner, repo_name)
        except Exception as e:
            errors["contributing"] = str(e)

        tree = []
        try:
            tree = gh.fetch_directory_tree(owner, repo_name, max_files=settings.max_repository_files)
        except Exception as e:
            errors["tree"] = str(e)

        dep_files = {}
        try:
            dep_files = gh.fetch_dependency_files(owner, repo_name)
        except Exception as e:
            errors["dep_files"] = str(e)

        # ── Fetch issues ──────────────────────────────────────────────────
        gh_issues = []
        try:
            gh_issues = gh.fetch_open_issues(owner, repo_name)
        except GitHubRateLimitError as e:
            errors["issues"] = str(e)
        except Exception as e:
            errors["issues"] = str(e)

        # ── Persist snapshot ──────────────────────────────────────────────
        now = datetime.now(timezone.utc)
        snapshot = RepositorySnapshot(
            id=str(uuid.uuid4()),
            repository_id=repo.id,
            sha=meta.get("default_branch"),
            raw_data=meta,
            directory_tree=tree,
            readme_content=readme,
            contributing_content=contributing,
            dependency_files=dep_files,
            fetched_at=now,
            expires_at=now + timedelta(hours=CACHE_TTL_HOURS),
        )
        session.add(snapshot)

        # ── Persist issues ─────────────────────────────────────────────────
        persisted_issues = _upsert_issues(gh_issues, repo.id, session)

        repo.last_analyzed_at = now
        repo.analysis_status = "done"
        session.flush()

        # ── Build result while session is still open ───────────────────────
        result = _build_result(repo, snapshot, persisted_issues, from_cache=False)
        result["fetch_errors"] = errors
        return result


def _upsert_issues(gh_issues: list, repository_id: str, session: Session) -> list:
    result = []
    for item in gh_issues:
        existing = session.query(Issue).filter_by(
            repository_id=repository_id, number=item["number"]
        ).first()
        if existing:
            issue = existing
        else:
            issue = Issue(
                id=str(uuid.uuid4()),
                repository_id=repository_id,
            )
            session.add(issue)

        issue.github_id = item["id"]
        issue.number = item["number"]
        issue.title = item["title"]
        issue.body = (item.get("body") or "")[:10000]
        issue.state = item.get("state", "open")
        issue.labels = [l["name"] for l in item.get("labels", [])]
        issue.assignees = [a["login"] for a in item.get("assignees", [])]
        issue.author = (item.get("user") or {}).get("login")
        issue.html_url = item["html_url"]
        issue.comments_count = item.get("comments", 0)

        if item.get("created_at"):
            issue.created_at_gh = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        if item.get("updated_at"):
            issue.updated_at_gh = datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00"))

        result.append(issue)

    session.flush()
    return result


def _build_result(
    repo: Repository,
    snapshot: Optional[RepositorySnapshot],
    issues: list,
    from_cache: bool,
) -> Dict[str, Any]:
    """
    Build a fully serialised plain-dict result while ORM objects are
    still attached to a live session.  Nothing in the returned dict
    holds a reference to a SQLAlchemy ORM object, so callers never
    trigger lazy-load after the session closes.
    """
    return {
        "repo": _repo_to_dict(repo),
        "snapshot": _snapshot_to_dict(snapshot),
        "issues": [_issue_to_dict(i) for i in issues],
        "from_cache": from_cache,
        "fetch_errors": {},
    }
