"""
Code search service — maps issue text to relevant files and symbols.
Uses keyword/token matching against the repository file tree and fetches
targeted file content for high-confidence matches.
No execution of repository code.
"""
from __future__ import annotations

import re
from typing import List, Dict, Optional, Tuple

from app.services.github_client import fetch_file_content
from app.core.config import get_settings


# ─── Token extraction ─────────────────────────────────────────────────────

_CAMEL_RE = re.compile(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])')
_IDENTIFIER_RE = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b')
_FILE_PATH_RE = re.compile(r'[\w/.\-]+\.\w{1,6}')
_ISSUE_NUM_RE = re.compile(r'#(\d+)')


def _tokenize(text: str) -> List[str]:
    """Extract meaningful tokens from issue text."""
    tokens = set()

    # Explicit file paths
    for match in _FILE_PATH_RE.finditer(text):
        tokens.add(match.group().lower())

    # Identifiers (function names, class names, etc.)
    for match in _IDENTIFIER_RE.finditer(text):
        word = match.group()
        tokens.add(word.lower())
        # Split camelCase
        parts = _CAMEL_RE.sub(' ', word).split()
        tokens.update(p.lower() for p in parts if len(p) > 2)

    # Remove stop words
    stop = {'the', 'and', 'for', 'with', 'this', 'that', 'from', 'are',
            'was', 'has', 'have', 'not', 'but', 'when', 'will', 'can',
            'should', 'would', 'could', 'also', 'been', 'being', 'into'}
    return [t for t in tokens if t not in stop and len(t) > 2]


def _score_file(file_path: str, tokens: List[str]) -> Tuple[float, str]:
    """
    Score a file path against issue tokens.
    Returns (score, match_type).
    """
    path_lower = file_path.lower()
    path_parts = re.split(r'[/.\-_]', path_lower)

    score = 0.0
    matched = []

    for token in tokens:
        # Exact path segment match (strong signal)
        if token in path_parts:
            score += 3.0
            matched.append(token)
        # Partial path match
        elif token in path_lower:
            score += 1.5
            matched.append(token)

    # Boost test files (may be highly relevant to bugs)
    if any(kw in path_lower for kw in ['test', 'spec', '__test__']):
        score *= 0.8  # slightly lower — don't flood with test files

    # Boost source files in key directories
    if any(kw in path_lower for kw in ['src/', 'lib/', 'core/', 'main', 'app/']):
        score *= 1.2

    if score >= 6.0:
        match_type = "direct_match"
    elif score >= 2.0:
        match_type = "related_reference"
    else:
        match_type = "ai_inferred"

    return score, match_type


def find_matching_test_file(source_path: str, all_tree_paths: List[str]) -> Optional[str]:
    """
    Finds the most likely automated test file corresponding to a given source file path.
    Supports Python, JavaScript/TypeScript, Go, Rust, Java conventions.
    """
    parts = source_path.replace("\\", "/").split("/")
    filename = parts[-1]
    name_no_ext = filename.rsplit(".", 1)[0]
    ext = filename.rsplit(".", 1)[1] if "." in filename else ""

    candidates = [
        f"test_{name_no_ext}.{ext}",
        f"{name_no_ext}_test.{ext}",
        f"{name_no_ext}.test.{ext}",
        f"{name_no_ext}.spec.{ext}",
        f"{name_no_ext}test.{ext}",
    ]

    # Search in all_tree_paths
    for path in all_tree_paths:
        path_lower = path.lower()
        if not any(k in path_lower for k in ["test", "spec"]):
            continue
        # Exact candidate filename match
        for cand in candidates:
            if path.endswith("/" + cand) or path == cand:
                return path

    # Fuzzy check: any test file containing the base name
    for path in all_tree_paths:
        path_lower = path.lower()
        if ("test" in path_lower or "spec" in path_lower) and name_no_ext.lower() in path_lower:
            return path

    return None


def extract_candidate_symbols(issue_text: str, file_path: str) -> List[str]:
    """
    Extracts high-likelihood function, class, or method symbols referenced in
    issue text or matching file nomenclature.
    """
    symbols = set()

    # Backticked code identifiers: `my_func()`, `ClassName`
    code_matches = re.findall(r'`([a-zA-Z_][a-zA-Z0-9_]{2,}(?:\(\))?)`', issue_text)
    for m in code_matches:
        symbols.add(m.rstrip("()"))

    # CamelCase identifiers
    camel_matches = re.findall(r'\b[A-Z][a-zA-Z0-9]{3,}\b', issue_text)
    for m in camel_matches[:6]:
        if m.lower() not in {"github", "python", "issue", "error", "traceback", "commit", "linux", "windows", "null"}:
            symbols.add(m)

    # Derived Class from basename
    base = file_path.rsplit("/", 1)[-1].split(".")[0]
    if "_" in base:
        camel_base = "".join(part.capitalize() for part in base.split("_"))
        symbols.add(camel_base)

    stop = {"None", "True", "False", "Exception", "Class", "Function", "Test", "Model"}
    filtered = [s for s in symbols if s not in stop and len(s) > 2]
    return sorted(filtered, key=len, reverse=True)[:4]


def search_code_for_issue(
    issue_title: str,
    issue_body: str,
    directory_tree: List[Dict],
    max_results: int = 8,
) -> List[Dict]:
    """
    Deterministic code search: maps issue text to relevant files using
    token matching against the repository tree.

    Returns list of:
      {path, score, match_type, reason, confidence, test_path, symbols, trail}

    All results are from the actual directory_tree — never fabricated.
    """
    text = f"{issue_title}\n{issue_body or ''}"
    tokens = _tokenize(text)

    if not tokens:
        return []

    all_blob_paths = [
        item.get("path", "") for item in directory_tree
        if item.get("type") == "blob"
    ]

    results = []
    for item in directory_tree:
        path = item.get("path", "")
        if item.get("type") != "blob":
            continue

        # Skip binary/generated files
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        skip_exts = {"png", "jpg", "jpeg", "gif", "svg", "ico", "woff", "ttf",
                     "eot", "mp4", "mp3", "pdf", "zip", "lock", "sum"}
        if ext in skip_exts:
            continue

        score, match_type = _score_file(path, tokens)
        if score < 1.0:
            continue

        # Build reason text
        matched_tokens = [t for t in tokens if t in path.lower()]
        if matched_tokens:
            reason = f"Path contains: {', '.join(matched_tokens[:4])}"
        else:
            reason = "Structurally related to issue scope"

        confidence = "high" if score >= 6.0 else ("medium" if score >= 2.5 else "low")
        test_path = find_matching_test_file(path, all_blob_paths)
        symbols = extract_candidate_symbols(text, path)

        sym_str = symbols[0] if symbols else "module"
        test_str = test_path or "No automated test identified"
        trail_breadcrumb = f"Issue -> {path} -> {sym_str} -> {test_str}"

        results.append({
            "path": path,
            "score": score,
            "match_type": match_type,
            "reason": reason,
            "confidence": confidence,
            "test_path": test_path,
            "symbols": symbols,
            "trail": trail_breadcrumb,
        })

    # Sort by score and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


def find_issue_relevant_snippets(
    owner: str,
    repo_name: str,
    file_paths: List[str],
    tokens: List[str],
    max_lines_per_file: int = 50,
) -> Dict[str, str]:
    """
    Fetch and extract relevant snippets from identified files.
    Returns {path: snippet} for the most relevant sections.
    Content is treated as untrusted; only text, no execution.
    """
    settings = get_settings()
    snippets = {}

    for path in file_paths[:4]:  # limit API calls
        content = fetch_file_content(owner, repo_name, path)
        if not content or content.startswith("[File too large"):
            continue

        lines = content.split("\n")
        relevant_lines = []

        for i, line in enumerate(lines):
            line_lower = line.lower()
            if any(token in line_lower for token in tokens):
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                relevant_lines.append((start, end, i))

        if not relevant_lines:
            # Just return first N lines
            snippets[path] = "\n".join(lines[:30])
            continue

        # Merge overlapping ranges
        merged_ranges = []
        for start, end, _ in sorted(relevant_lines):
            if merged_ranges and start <= merged_ranges[-1][1]:
                merged_ranges[-1] = (merged_ranges[-1][0], max(merged_ranges[-1][1], end))
            else:
                merged_ranges.append((start, end))

        snippet_parts = []
        for start, end in merged_ranges[:5]:
            chunk = lines[start:end]
            snippet_parts.append(f"# Lines {start+1}-{end}\n" + "\n".join(chunk))

        snippets[path] = "\n...\n".join(snippet_parts)[:3000]

    return snippets
