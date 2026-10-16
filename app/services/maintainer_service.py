"""
Maintainer Studio Service for RepoCompass.
Implements:
  1. Issue quality checks and 'needs-more-information' classification
  2. Grounded and AI-assisted issue improvement drafting
  3. Beginner-friendly starter-task generation
  4. Post-merge related open issues discovery
  5. Draft approval and persistence
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.services.llm_service import (
    generate_json, SYSTEM_PROMPT, check_ollama_available,
    LLMUnavailableError, LLMOutputError
)


def analyze_issue_quality(issue: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates issue completeness, clarity, reproduction steps, and context.
    """
    body = (issue.get("body") or "").strip()
    title = (issue.get("title") or "").strip()
    labels = issue.get("labels", [])
    assignees = issue.get("assignees", [])

    is_bug = any(kw in (title + " " + body).lower() for kw in ["bug", "fix", "error", "crash", "fails", "failed", "broken", "traceback"])

    has_repro = bool(re.search(r"(steps? to reproduce|reproduc|how to repro|to reproduce|expected behavior)", body, re.IGNORECASE))
    has_logs = bool("```" in body or re.search(r"(traceback|error|exception|log|stack trace)", body, re.IGNORECASE))

    checks = {
        "has_description": len(body) >= 50,
        "has_repro_steps": has_repro if is_bug else True,
        "has_expected_vs_actual": bool(re.search(r"(expected|actual|instead of|should be|current behavior|purpose)", body, re.IGNORECASE)),
        "has_logs_or_code": has_logs if is_bug else bool("```" in body or "`" in body or len(body) > 70),
        "has_acceptance_criteria": bool(re.search(r"(acceptance|criteria|definition of done|expected result|requirement)", body, re.IGNORECASE)),
        "is_unassigned": len(assignees) == 0,
        "has_labels": len(labels) > 0,
    }

    # Quality score out of 100
    weights = {
        "has_description": 25,
        "has_repro_steps": 25,
        "has_expected_vs_actual": 20,
        "has_logs_or_code": 15,
        "has_acceptance_criteria": 10,
        "has_labels": 5,
    }
    score = sum(w for k, w in weights.items() if checks[k])

    missing_items = []
    if not checks["has_description"]:
        missing_items.append("Missing detailed problem description")
    if is_bug and not has_repro:
        missing_items.append("No explicit reproduction steps")
    if is_bug and not checks["has_expected_vs_actual"]:
        missing_items.append("Unclear expected vs actual behavior")
    if is_bug and not has_logs:
        missing_items.append("No error logs, stack trace, or code block")

    needs_more_info = score < 45 or len(body) < 35

    return {
        "checks": checks,
        "quality_score": score,
        "missing_items": missing_items,
        "needs_more_info": needs_more_info,
    }


def classify_issue_maintainer(issue: Dict[str, Any], base_difficulty: str) -> str:
    """
    Classifies issue as beginner, intermediate, advanced, or needs-more-information.
    """
    quality = analyze_issue_quality(issue)
    if quality["needs_more_info"]:
        return "needs-more-information"
    return base_difficulty if base_difficulty in ["beginner", "intermediate", "advanced"] else "intermediate"


def generate_grounded_improvement_draft(issue: Dict[str, Any], quality: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produces an improved, structured version of the issue grounded in existing data.
    """
    title = issue.get("title", "")
    body = (issue.get("body") or "").strip()
    missing = quality.get("missing_items", [])

    improved_title = f"[Clarified] {title}" if not title.startswith("[") else title

    body_sections = [
        "## Problem Description",
        body if body else "*(Please describe the issue in detail)*",
        "",
        "## Steps to Reproduce",
        "1. Configure the environment as specified in README/setup.",
        "2. Execute the routine triggering this condition.",
        "3. Observe the reported behavior.",
        "",
        "## Expected Behavior",
        "The operation should complete gracefully without unexpected termination or unhandled errors.",
        "",
        "## Actual Behavior",
        "Observed behavior diverges from expected specification.",
        "",
        "## Acceptance Criteria",
        "- [ ] Root cause identified and covered by automated test",
        "- [ ] Regression test passes with minimal defensive patch",
        "- [ ] No breakages in existing test suite",
    ]

    rationale = f"Addressed {len(missing)} missing items: {', '.join(missing)}." if missing else "Structured for contributor clarity."

    return {
        "improved_title": improved_title,
        "improved_body": "\n".join(body_sections),
        "suggested_labels": issue.get("labels", []) + ["needs-triage"],
        "rationale": rationale,
        "source": "grounded_heuristic",
    }


def generate_grounded_starter_draft(issue: Dict[str, Any], likely_files: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generates a beginner-friendly scoped starter issue derived from the original issue.
    """
    title = issue.get("title", "")
    num = issue.get("number", "")
    files_str = "\n".join(f"- `{f}`" for f in (likely_files or [])[:3]) if likely_files else "- Relevant module in `src/` or `app/`"

    starter_title = f"good first issue: Scoped starter task for #{num} - {title[:50]}"
    starter_body = f"""### Summary
This is a beginner-friendly starter issue split from parent issue #{num}.

### Scope & Objective
Create an isolated unit test or apply a focused defensive check for:
> "{title}"

### Files to Inspect
{files_str}

### Step-by-Step Guide
1. Fork the repository and create a branch `fix/issue-{num}-starter`.
2. Locate the target file above.
3. Add a focused unit test reproducing the case.
4. Verify tests pass using the project's test runner.
5. Open a Pull Request referencing issue #{num}.

### Acceptance Criteria
- [ ] Automated test added covering this scenario
- [ ] Existing tests continue to pass
"""

    return {
        "starter_title": starter_title,
        "starter_body": starter_body,
        "scope_explanation": "Scoped to an isolated unit test and single-file check appropriate for new contributors.",
        "likely_files": likely_files or [],
        "estimated_hours": 2,
        "source": "grounded_heuristic",
    }


def find_related_issues_for_pr(
    changed_files: List[str],
    all_issues: List[Dict[str, Any]],
    pr_description: str = "",
) -> List[Dict[str, Any]]:
    """
    Scans open issues to find candidate issues related to a merged PR's changed files and symbols.
    """
    related = []
    file_basenames = {f.rsplit("/", 1)[-1].split(".")[0].lower() for f in changed_files if "/" in f or "." in f}

    for issue in all_issues:
        title = (issue.get("title") or "").lower()
        body = (issue.get("body") or "").lower()
        issue_text = f"{title} {body}"

        matched_files = [f for f in changed_files if f.lower() in issue_text or (f.rsplit("/", 1)[-1].lower() in issue_text)]
        matched_bases = [b for b in file_basenames if b in issue_text and len(b) > 3]

        score = len(matched_files) * 3 + len(matched_bases) * 1.5

        if score > 0:
            reasons = []
            if matched_files:
                reasons.append(f"Shares modified files: {', '.join(matched_files[:2])}")
            if matched_bases:
                reasons.append(f"References component: {', '.join(matched_bases[:2])}")

            related.append({
                "number": issue.get("number"),
                "title": issue.get("title"),
                "html_url": issue.get("html_url", "#"),
                "score": score,
                "reasons": reasons,
                "labels": issue.get("labels", []),
            })

    related.sort(key=lambda x: x["score"], reverse=True)
    return related[:10]
