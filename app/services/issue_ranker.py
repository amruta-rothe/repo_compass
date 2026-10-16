"""
Issue scoring service — deterministic, explainable ranking.
LLM is used only for explanations, not for the score itself.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from app.db.models import Issue, IssueScore, Profile


# ─── Label matchers ───────────────────────────────────────────────────────

_BEGINNER_LABELS = {
    "good first issue", "good-first-issue", "beginner", "beginner-friendly",
    "easy", "starter", "first-timers-only", "first timers only",
    "help wanted", "hacktoberfest",
}

_DOCS_LABELS = {"documentation", "docs", "doc"}
_BUG_LABELS = {"bug", "defect", "fix"}
_FEATURE_LABELS = {"enhancement", "feature", "feat", "new feature"}

_BLOCKED_LABELS = {"blocked", "wip", "in progress", "do not merge", "needs investigation"}

# ─── Scoring signals ──────────────────────────────────────────────────────

def _label_set(issue: Issue) -> set:
    return {l.lower() for l in (issue.labels or [])}


def _is_assigned(issue: Issue) -> bool:
    return bool(issue.assignees)


def _days_stale(issue: Issue) -> Optional[float]:
    if not issue.updated_at_gh:
        return None
    updated = issue.updated_at_gh
    if isinstance(updated, str):
        try:
            updated = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except Exception:
            return None
    if getattr(updated, "tzinfo", None) is None:
        updated = updated.replace(tzinfo=timezone.utc)
    else:
        updated = updated.astimezone(timezone.utc)
    delta = datetime.now(timezone.utc) - updated
    return delta.days


def _body_quality(body: str) -> float:
    """Heuristic: body length + has code blocks + has clear description."""
    if not body or len(body.strip()) < 30:
        return 0.0
    score = min(len(body) / 2000, 1.0) * 0.5
    if "```" in body or "`" in body:
        score += 0.2
    if any(kw in body.lower() for kw in ["steps to reproduce", "expected", "actual", "acceptance"]):
        score += 0.3
    return min(score, 1.0)


def _language_match(issue: Issue, profile: Optional[Profile]) -> float:
    if not profile or not profile.programming_languages:
        return 0.0
    text = f"{issue.title} {issue.body or ''}".lower()
    languages = [l.lower() for l in profile.programming_languages]
    matches = sum(1 for lang in languages if lang in text)
    return min(matches / max(len(languages), 1), 1.0)


def score_issue(issue: Issue, profile: Optional[Profile] = None) -> Tuple[float, Dict, str]:
    """
    Returns (total_score 0–100, signals_dict, difficulty_estimate).
    Signals: each has value, weight, reason.
    """
    labels = _label_set(issue)
    signals = {}
    total = 0.0

    # 1. Beginner / help-wanted labels  (+25 max)
    beginner_match = bool(labels & _BEGINNER_LABELS)
    signals["beginner_label"] = {
        "value": int(beginner_match),
        "weight": 25,
        "reason": "Labeled as beginner-friendly / help wanted" if beginner_match else "No beginner label",
    }
    if beginner_match:
        total += 25

    # 2. Assignment status  (+0 if unassigned; big penalty if assigned)
    assigned = _is_assigned(issue)
    signals["assignment"] = {
        "value": int(not assigned),
        "weight": -30,
        "reason": "Has assignees — may already be in progress" if assigned else "No assignee listed",
    }
    if assigned:
        total -= 30

    # 3. Blocked labels  (-20 if blocked)
    blocked = bool(labels & _BLOCKED_LABELS)
    signals["blocked"] = {
        "value": int(blocked),
        "weight": -20,
        "reason": "Blocked or WIP label present" if blocked else "Not blocked",
    }
    if blocked:
        total -= 20

    # 4. Body quality  (0–20)
    bq = _body_quality(issue.body or "")
    bq_pts = bq * 20
    signals["body_quality"] = {
        "value": round(bq, 2),
        "weight": 20,
        "reason": f"Issue body quality score: {bq:.0%}",
    }
    total += bq_pts

    # 5. Recency  (0–15: penalize stale)
    stale_days = _days_stale(issue)
    if stale_days is None:
        recency_pts = 5
        recency_note = "Activity date unknown"
    elif stale_days > 180:
        recency_pts = 0
        recency_note = f"Stale: no activity in {stale_days:.0f} days"
    elif stale_days > 90:
        recency_pts = 5
        recency_note = f"Moderately stale ({stale_days:.0f} days)"
    else:
        recency_pts = 15
        recency_note = f"Active recently ({stale_days:.0f} days ago)"
    signals["recency"] = {"value": stale_days, "weight": 15, "reason": recency_note}
    total += recency_pts

    # 6. Documentation scope  (+10)
    is_docs = bool(labels & _DOCS_LABELS)
    if is_docs:
        total += 10
    signals["docs_scope"] = {
        "value": int(is_docs),
        "weight": 10,
        "reason": "Documentation issue (lower code risk)" if is_docs else "Not a docs issue",
    }

    # 7. Language / skill match  (0–10)
    lang_score = _language_match(issue, profile)
    lang_pts = lang_score * 10
    total += lang_pts
    signals["language_match"] = {
        "value": round(lang_score, 2),
        "weight": 10,
        "reason": f"Language match to your profile: {lang_score:.0%}",
    }

    # Clamp
    total = max(0.0, min(100.0, total))

    # Difficulty estimate
    if total >= 55 or beginner_match:
        difficulty = "beginner"
    elif total >= 30:
        difficulty = "intermediate"
    else:
        difficulty = "advanced"

    # Override difficulty for assigned/blocked issues
    if assigned or blocked:
        difficulty = "unavailable"

    return round(total, 1), signals, difficulty


def rank_issues(
    issues: List[Issue],
    profile: Optional[Profile] = None,
    exclude_assigned: bool = False,
    exclude_stale_days: Optional[int] = None,
) -> List[Tuple[Issue, float, Dict, str]]:
    """
    Returns list of (issue, score, signals, difficulty) sorted by score desc.
    Filters closed issues. Optionally excludes assigned or stale issues.
    """
    results = []
    for issue in issues:
        if issue.state != "open":
            continue
        if exclude_assigned and _is_assigned(issue):
            continue
        stale = _days_stale(issue)
        if exclude_stale_days and stale and stale > exclude_stale_days:
            continue

        score, signals, difficulty = score_issue(issue, profile)
        results.append((issue, score, signals, difficulty))

    results.sort(key=lambda x: x[1], reverse=True)
    return results
