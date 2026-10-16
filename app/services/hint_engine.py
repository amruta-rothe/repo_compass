"""
Adaptive Hint Engine for RepoCompass.
Implements the 5-level progressive hint ladder defined in PRD Section 5.7:
  Level 1: Concept
  Level 2: Module/Directory
  Level 3: Specific File
  Level 4: Function or Test to Inspect
  Level 5: Suggested Implementation Approach

Combines instant grounded heuristic guidance with Ollama Qwen3 AI enrichment.
Adapts hint depth and style to the contributor's experience level (beginner, intermediate, advanced).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.services.llm_service import (
    generate, generate_stream, build_hint_prompt, SYSTEM_PROMPT,
    check_ollama_available, LLMUnavailableError,
)


def _generate_grounded_hint(
    issue: Dict[str, Any],
    hint_level: int,
    relevant_files: List[str],
    exp_level: str = "beginner",
    repo_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Deterministic progressive hint generator derived directly from issue metadata,
    identified files, and repo structure.
    """
    title = issue.get("title", "")
    body = issue.get("body", "") or ""
    labels = issue.get("labels", [])
    top_file = relevant_files[0] if relevant_files else None
    repo_name = (repo_data or {}).get("full_name", "this repository")

    # Clean symbols from title
    words = [w.strip("`(),:;'\"") for w in title.split() if len(w) > 3]
    key_terms = [w for w in words if w.lower() not in {"fix", "bug", "issue", "error", "fails", "failed", "when", "with", "does"}]
    main_subject = key_terms[0] if key_terms else "the reported behavior"

    if hint_level == 1:
        # Concept Level
        label_text = f"Tagged with: {', '.join(labels[:3])}. " if labels else ""
        if exp_level == "beginner":
            return (
                f"**Concept Overview:** This issue focuses on **{main_subject}**. {label_text}"
                f"The core goal is to understand how {repo_name} expects inputs and operations "
                f"related to this feature to behave under standard vs unexpected conditions."
            )
        elif exp_level == "advanced":
            return (
                f"**Architecture Scope:** Involves **{main_subject}** invariant handling. {label_text}"
                f"Inspect state transitions and boundary conditions governing this subsystem."
            )
        else:
            return (
                f"**Subsystem Concept:** Pertains to **{main_subject}**. {label_text}"
                f"Focus on the data contract and validation expectations established for this component."
            )

    elif hint_level == 2:
        # Module / Directory Level
        if top_file and "/" in top_file:
            module_dir = top_file.rsplit("/", 1)[0]
            return (
                f"**Target Module/Directory:** Look in the `[dir] {module_dir}/` directory. "
                f"This subsystem contains the core logic responsible for managing {main_subject}."
            )
        return (
            f"**Target Module:** Look in the primary source directory (`src/` or `app/`). "
            f"Search for files referencing '{main_subject}'."
        )

    elif hint_level == 3:
        # Specific File Level
        if top_file:
            other_files = [f for f in relevant_files[1:3] if f != top_file]
            others_msg = f" (Related: `{', '.join(other_files)}`)" if other_files else ""
            return (
                f"**Target File:** Start by inspecting `{top_file}`{others_msg}. "
                f"Review the imports, class definitions, and helper routines defined in this file."
            )
        return (
            f"**Target File:** Check the files listed in the **Issue -> Code Trail** table on the left. "
            f"Start with the file that has the highest match confidence."
        )

    elif hint_level == 4:
        # Function or Test to Inspect
        test_file = next((f for f in relevant_files if "test" in f.lower() or "spec" in f.lower()), None)
        test_advice = f"Review the test suite in `{test_file}` to see existing assertions." if test_file else "Search `tests/` for existing test cases covering this file."

        # Find potential function name
        funcs = re.findall(r'`([a-zA-Z_][a-zA-Z0-9_]{2,})\(\)`', title + " " + body)
        func_advice = f"Pay close attention to function `{funcs[0]}()`." if funcs else f"Look for functions handling {main_subject}."

        return (
            f"**Symbol & Test Inspection:**\n"
            f"- **Code to check:** {func_advice}\n"
            f"- **Test verification:** {test_advice}"
        )

    else:
        # Implementation Approach (Level 5)
        return (
            f"**Suggested Implementation Strategy:**\n"
            f"1. **Reproduce First:** In your local environment, write a failing unit test that triggers the issue reported in #{issue.get('number')}.\n"
            f"2. **Minimal Edit:** Locate the condition or transformation in `{top_file or 'the target file'}` and apply the minimal defensive fix or logic branch.\n"
            f"3. **Run Regression:** Run the test suite to confirm your new test passes without breaking existing tests.\n"
            f"4. **Draft Patch:** Go to the Practice Lab to review your proposed patch before opening a PR."
        )


def generate_adaptive_hint(
    issue: Dict[str, Any],
    hint_level: int,
    relevant_files: List[str],
    exp_level: str = "beginner",
    repo_data: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generates a progressive hint for the given level.
    Tries Ollama first; falls back gracefully to grounded heuristic hints on timeout/error.
    """
    hint_level = max(1, min(5, hint_level))
    grounded_hint = _generate_grounded_hint(
        issue=issue,
        hint_level=hint_level,
        relevant_files=relevant_files,
        exp_level=exp_level,
        repo_data=repo_data,
    )

    if not check_ollama_available():
        return grounded_hint

    prompt = build_hint_prompt(
        issue_title=issue.get("title", ""),
        issue_body=issue.get("body", ""),
        hint_level=hint_level,
        relevant_files=relevant_files,
        experience_level=exp_level,
    )

    try:
        ai_hint = generate(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=250,
        )
        if ai_hint and len(ai_hint.strip()) > 20:
            return ai_hint.strip()
    except (LLMUnavailableError, Exception):
        pass

    return grounded_hint


def stream_adaptive_hint(
    issue: Dict[str, Any],
    hint_level: int,
    relevant_files: List[str],
    exp_level: str = "beginner",
    repo_data: Optional[Dict[str, Any]] = None,
):
    """
    Yield the hint progressively so the UI can render it as it is generated.

    Falls back to the deterministic grounded hint when Ollama is unavailable or
    produces nothing useful. Same content contract as `generate_adaptive_hint`,
    just streamed.
    """
    hint_level = max(1, min(5, hint_level))
    grounded_hint = _generate_grounded_hint(
        issue=issue,
        hint_level=hint_level,
        relevant_files=relevant_files,
        exp_level=exp_level,
        repo_data=repo_data,
    )

    if not check_ollama_available():
        yield grounded_hint
        return

    prompt = build_hint_prompt(
        issue_title=issue.get("title", ""),
        issue_body=issue.get("body", ""),
        hint_level=hint_level,
        relevant_files=relevant_files,
        experience_level=exp_level,
    )

    collected: List[str] = []
    try:
        for chunk in generate_stream(
            prompt,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=250,
        ):
            collected.append(chunk)
            yield chunk
    except Exception:
        pass

    # If the model produced nothing usable, fall back to grounded guidance.
    if len("".join(collected).strip()) <= 20:
        yield grounded_hint
