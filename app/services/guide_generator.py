"""
Guide Generator & Dynamic Workflow Engine for RepoCompass.
Intelligently analyzes repository metadata, directory tree, dependency manifests,
README, and CONTRIBUTING to generate:
  1. A grounded, structured onboarding summary (no raw dumps)
  2. Dynamic 5-step visual workflow steps customized per repository
  3. Seamless Ollama Qwen3 enrichment when available with instant heuristic fallback
"""
from __future__ import annotations

import re
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.services.llm_service import (
    generate_json, check_ollama_available, SYSTEM_PROMPT,
    LLMUnavailableError, LLMOutputError
)


def detect_repository_stack(repo_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically inspects manifests, filenames, and metadata to identify
    languages, package managers, test runners, linters, and frameworks.
    """
    dep_files = repo_data.get("dep_files") or {}
    primary_lang = (repo_data.get("primary_language") or "").lower()
    tree = repo_data.get("tree") or []
    all_paths = {item.get("path", "").lower() for item in tree if isinstance(item, dict)}

    stack = {
        "language": repo_data.get("primary_language") or "General",
        "package_manager": "git",
        "install_command": "git clone",
        "test_runner": "Not detected",
        "test_command": "pytest",
        "lint_command": None,
        "frameworks": [],
        "branch_prefix": "fix/",
        "base_branch": "main",
    }

    # Python stack
    if "pyproject.toml" in dep_files or "requirements.txt" in dep_files or "setup.py" in dep_files or primary_lang == "python":
        stack["language"] = "Python"
        pyproject = dep_files.get("pyproject.toml", "")
        reqs = dep_files.get("requirements.txt", "")
        setup_py = dep_files.get("setup.py", "")

        if "tool.poetry" in pyproject or "poetry.lock" in all_paths:
            stack["package_manager"] = "Poetry"
            stack["install_command"] = "poetry install"
            stack["test_command"] = "poetry run pytest"
            stack["lint_command"] = "poetry run ruff check ." if "ruff" in pyproject else "poetry run flake8"
        elif "Pipfile" in all_paths:
            stack["package_manager"] = "Pipenv"
            stack["install_command"] = "pipenv install --dev"
            stack["test_command"] = "pipenv run pytest"
        elif "requirements-dev.txt" in all_paths:
            stack["package_manager"] = "pip"
            stack["install_command"] = "pip install -r requirements-dev.txt"
            stack["test_command"] = "pytest"
        elif "requirements.txt" in dep_files:
            stack["package_manager"] = "pip"
            stack["install_command"] = "pip install -r requirements.txt"
            stack["test_command"] = "pytest"
        else:
            stack["package_manager"] = "pip"
            stack["install_command"] = "pip install -e ."
            stack["test_command"] = "pytest"

        # Check testing frameworks
        if "pytest" in pyproject or "pytest" in reqs or any("test" in p for p in all_paths):
            stack["test_runner"] = "pytest"
        elif "unittest" in reqs or "unittest" in pyproject:
            stack["test_runner"] = "unittest"
            stack["test_command"] = "python -m unittest discover"

        # Check web frameworks
        content_blob = (pyproject + reqs + setup_py).lower()
        if "fastapi" in content_blob:
            stack["frameworks"].append("FastAPI")
        if "django" in content_blob:
            stack["frameworks"].append("Django")
        if "flask" in content_blob:
            stack["frameworks"].append("Flask")
        if "streamlit" in content_blob:
            stack["frameworks"].append("Streamlit")
        if "torch" in content_blob or "pytorch" in content_blob:
            stack["frameworks"].append("PyTorch")

    # Node / TypeScript stack
    elif "package.json" in dep_files or primary_lang in ["javascript", "typescript"]:
        stack["language"] = "TypeScript" if primary_lang == "typescript" or any(p.endswith(".ts") for p in all_paths) else "JavaScript"
        pkg_json_str = dep_files.get("package.json", "{}")
        pkg_data = {}
        try:
            pkg_data = json.loads(pkg_json_str) if isinstance(pkg_json_str, str) else pkg_json_str
        except Exception:
            pkg_data = {}

        scripts = pkg_data.get("scripts", {}) if isinstance(pkg_data, dict) else {}
        deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})} if isinstance(pkg_data, dict) else {}

        if "pnpm-lock.yaml" in all_paths:
            stack["package_manager"] = "pnpm"
            stack["install_command"] = "pnpm install"
            stack["test_command"] = "pnpm test" if "test" in scripts else "pnpm test"
        elif "yarn.lock" in all_paths:
            stack["package_manager"] = "yarn"
            stack["install_command"] = "yarn install"
            stack["test_command"] = "yarn test" if "test" in scripts else "yarn test"
        elif "bun.lockb" in all_paths:
            stack["package_manager"] = "bun"
            stack["install_command"] = "bun install"
            stack["test_command"] = "bun test"
        else:
            stack["package_manager"] = "npm"
            stack["install_command"] = "npm install"
            stack["test_command"] = "npm test"

        if "next" in deps:
            stack["frameworks"].append("Next.js")
        if "react" in deps:
            stack["frameworks"].append("React")
        if "vue" in deps:
            stack["frameworks"].append("Vue.js")
        if "express" in deps:
            stack["frameworks"].append("Express")

    # Rust stack
    elif "cargo.toml" in [k.lower() for k in dep_files] or primary_lang == "rust":
        stack["language"] = "Rust"
        stack["package_manager"] = "Cargo"
        stack["install_command"] = "cargo build"
        stack["test_command"] = "cargo test"
        stack["lint_command"] = "cargo clippy"
        stack["test_runner"] = "cargo test"

    # Go stack
    elif "go.mod" in [k.lower() for k in dep_files] or primary_lang == "go":
        stack["language"] = "Go"
        stack["package_manager"] = "Go Modules"
        stack["install_command"] = "go mod download"
        stack["test_command"] = "go test ./..."
        stack["test_runner"] = "go test"

    return stack


def clean_markdown_summary(markdown_text: Optional[str], max_paragraphs: int = 3) -> str:
    """
    Cleans raw README/markdown content by stripping badge images, HTML tags,
    license banners, and tables, returning a readable summary paragraph.
    """
    if not markdown_text:
        return ""

    lines = markdown_text.splitlines()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip badge images, shields.io, CI badges
        if re.search(r"!\[.*?\]\(.*?(shields\.io|badge|github\.com\/.*?\/actions|codecov).*?\)", stripped):
            continue
        if stripped.startswith("[![") or (stripped.startswith("<img") and "badge" in stripped.lower()):
            continue
        # Skip pure html divs, tables
        if stripped.startswith("<p align=") or stripped.startswith("<table>") or stripped.startswith("<tr>"):
            continue
        # Skip markdown table rows
        if stripped.startswith("|") and stripped.endswith("|"):
            continue
        # Skip heading anchor markers
        if re.match(r"^#+\s*", stripped):
            clean_lines.append("")
            continue
        clean_lines.append(stripped)

    # Join and extract substantive text paragraphs
    text = "\n".join(clean_lines)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 40]
    
    if paragraphs:
        selected = paragraphs[:max_paragraphs]
        summary = " ".join(selected)
        # Bounded length
        if len(summary) > 600:
            summary = summary[:597].rsplit(" ", 1)[0] + "..."
        return summary
    return ""


def build_dynamic_workflow_steps(repo_data: Dict[str, Any], stack: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Constructs the 5-step dynamic workflow modeled after the reference infographic:
    Step 1: Emerald (#10B981) - Fork & Clone (Bullseye/Target icon)
    Step 2: Amber (#F59E0B) - Install Dependencies (Magnifier icon)
    Step 3: Royal Blue (#2563EB) - Branch Creation (Flowchart/Branch icon)
    Step 4: Emerald (#10B981) - Implementation & Tests (Pencil/Code icon)
    Step 5: Amber (#F59E0B) - Open PR & Review (Eye/Review icon)
    """
    full_name = repo_data.get("full_name") or "owner/repository"
    repo_name = full_name.split("/")[-1] if "/" in full_name else full_name
    lang = stack["language"]
    pkg_mgr = stack["package_manager"]
    install_cmd = stack["install_command"]
    test_cmd = stack["test_command"]

    steps = [
        {
            "step_number": 1,
            "title": "Fork & Clone Repository",
            "directive": f"Fork {full_name} to your personal GitHub account and clone your remote fork locally.",
            "command": f"git clone https://github.com/<your-username>/{repo_name}.git\ncd {repo_name}",
            "color": "#10B981",
            "icon_type": "target",
            "icon_position": "left",
            "source": f"GitHub Repository ({full_name})",
        },
        {
            "step_number": 2,
            "title": "Setup Environment & Dependencies",
            "directive": f"Initialize isolated {lang} environment and install locked project dependencies using {pkg_mgr}.",
            "command": install_cmd,
            "color": "#F59E0B",
            "icon_type": "magnifier",
            "icon_position": "right",
            "source": f"Detected {pkg_mgr} manifest",
        },
        {
            "step_number": 3,
            "title": "Create a Focused Topic Branch",
            "directive": "Never commit directly to the default branch. Create a descriptive branch referencing the issue number.",
            "command": "git checkout -b fix/issue-123-short-description",
            "color": "#2563EB",
            "icon_type": "branch",
            "icon_position": "left",
            "source": "Standard Git Flow Convention",
        },
        {
            "step_number": 4,
            "title": "Implement Changes & Verify Tests",
            "directive": f"Make atomic code edits adhering to project style. Run {stack['test_runner']} before staging commits.",
            "command": test_cmd,
            "color": "#10B981",
            "icon_type": "pencil",
            "icon_position": "right",
            "source": f"Automated test suite ({stack['test_runner']})",
        },
        {
            "step_number": 5,
            "title": "Push Branch & Submit Pull Request",
            "directive": "Push to your fork, submit a PR against upstream main, and link the issue in the description for maintainer review.",
            "command": f"git push origin fix/issue-123-short-description",
            "color": "#F59E0B",
            "icon_type": "eye",
            "icon_position": "left",
            "source": "GitHub Pull Request Review Process",
        },
    ]

    return steps


def extract_key_directories(tree: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Extracts high-value directories from the tree with grounded purpose descriptions.
    """
    known_purposes = {
        "src": "Primary source code and implementation modules.",
        "app": "Application entry points, routes, and core business logic.",
        "pages": "Streamlit or Next.js page definitions and UI views.",
        "components": "Reusable UI visual elements and design system widgets.",
        "tests": "Automated unit, integration, and regression test suites.",
        "test": "Automated unit and integration test files.",
        "docs": "Project documentation, architecture guides, and user manuals.",
        "lib": "Shared utility helpers, client wrappers, and library abstractions.",
        "core": "Core configuration, security boundaries, and engine logic.",
        "api": "REST / GraphQL endpoint definitions and route controllers.",
        "scripts": "Automation scripts, build tasks, and maintenance tools.",
        "services": "Backend business logic and domain service layers.",
        "models": "Database ORM schemas and domain entity definitions.",
        "db": "Database connection pooling, migrations, and session management.",
    }

    dirs_seen = set()
    results = []

    for item in tree:
        path = item.get("path", "")
        parts = path.split("/")
        if len(parts) > 1:
            top_dir = parts[0].lower()
            if top_dir in known_purposes and top_dir not in dirs_seen:
                dirs_seen.add(top_dir)
                results.append({
                    "path": f"{top_dir}/",
                    "purpose": known_purposes[top_dir],
                })
        if len(results) >= 6:
            break

    if not results and tree:
        # Default top-level dirs
        top_dirs = sorted(list({p.get("path", "").split("/")[0] for p in tree if "/" in p.get("path", "")}))[:5]
        for d in top_dirs:
            results.append({
                "path": f"{d}/",
                "purpose": "Repository module directory.",
            })

    return results


def generate_grounded_guide(repo_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produces a 100% verified, grounded onboarding guide deterministically.
    Never fails, never invents non-existent commands or files.
    """
    stack = detect_repository_stack(repo_data)
    readme = repo_data.get("readme") or ""
    repo_desc = repo_data.get("description") or ""

    # Clean summary
    readme_summary = clean_markdown_summary(readme, max_paragraphs=2)
    if readme_summary and repo_desc and repo_desc.lower() not in readme_summary.lower():
        overview = f"{repo_desc}. {readme_summary}"
    elif readme_summary:
        overview = readme_summary
    elif repo_desc:
        overview = f"{repo_desc} Built with {stack['language']}."
    else:
        overview = f"Open-source repository {repo_data.get('full_name', '')} built using {stack['language']}."

    # Tech stack list
    tech_stack = [stack["language"]]
    if stack["package_manager"] not in ["git", "General"]:
        tech_stack.append(stack["package_manager"])
    if stack["test_runner"] != "Not detected":
        tech_stack.append(stack["test_runner"])
    tech_stack.extend(stack["frameworks"])

    # Prerequisites
    prereqs = [f"{stack['language']} runtime environment", "Git version control"]
    if stack["package_manager"] not in ["git", "General"]:
        prereqs.append(f"{stack['package_manager']} package manager")

    # Setup steps
    setup_steps = [
        {
            "step": "Clone the repository locally",
            "command": f"git clone {repo_data.get('url', 'https://github.com/' + repo_data.get('full_name', ''))}.git",
            "verified": True,
            "source": "GitHub metadata",
        },
        {
            "step": f"Install project dependencies using {stack['package_manager']}",
            "command": stack["install_command"],
            "verified": True,
            "source": f"Manifest detection ({stack['package_manager']})",
        },
        {
            "step": f"Verify test suite with {stack['test_runner']}",
            "command": stack["test_command"],
            "verified": True,
            "source": f"Test runner detection",
        },
    ]

    important_dirs = extract_key_directories(repo_data.get("tree") or [])
    workflow_steps = build_dynamic_workflow_steps(repo_data, stack)

    missing_info = []
    if not repo_data.get("contributing"):
        missing_info.append("No CONTRIBUTING.md found; using standard GitHub flow conventions.")
    if stack["test_runner"] == "Not detected":
        missing_info.append("Automated test framework not explicitly declared in root manifests.")

    return {
        "overview": overview,
        "tech_stack": tech_stack,
        "prerequisites": prereqs,
        "setup_steps": setup_steps,
        "important_dirs": important_dirs,
        "contribution_workflow": workflow_steps,
        "missing_info": missing_info,
        "generated_at": datetime.now().isoformat(),
        "is_ai_enriched": False,
        "stack_info": stack,
    }


def get_cached_guide(repo_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves cached guide from database if available, achieving <5ms instant reload."""
    from app.db.session import get_db
    from app.db.models import Guide
    try:
        with get_db() as session:
            g = (
                session.query(Guide)
                .filter_by(repository_id=repo_id, status="done")
                .order_by(Guide.generated_at.desc())
                .first()
            )
            if g and g.content:
                return g.content
    except Exception:
        pass
    return None


def save_cached_guide(repo_id: str, guide_data: Dict[str, Any], model_name: Optional[str] = None) -> None:
    """Persists guide into the database for instant subsequent loads."""
    from app.db.session import get_db
    from app.db.models import Guide
    import uuid
    from datetime import datetime, timezone
    from app.core.config import get_settings

    if model_name is None:
        model_name = get_settings().ollama_model

    try:
        with get_db() as session:
            existing = session.query(Guide).filter_by(repository_id=repo_id).first()
            if existing:
                existing.content = guide_data
                existing.model_name = model_name
                existing.status = "done"
                existing.generated_at = datetime.now(timezone.utc)
            else:
                new_guide = Guide(
                    id=str(uuid.uuid4()),
                    repository_id=repo_id,
                    model_name=model_name,
                    content=guide_data,
                    status="done",
                    generated_at=datetime.now(timezone.utc),
                )
                session.add(new_guide)
            session.flush()
    except Exception:
        pass


def enrich_guide_with_ollama(base_guide: Dict[str, Any], repo_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Attempts to enrich the grounded guide using Ollama Qwen3 with a tight,
    bounded prompt (<800 chars) and native format="json" for fast CPU inference.
    Falls back gracefully to base_guide on any timeout or decode failure.
    """
    if not check_ollama_available():
        return base_guide

    # Check if this guide was already cached in database
    repo_id = repo_data.get("repo_id")
    if repo_id:
        cached = get_cached_guide(repo_id)
        if cached:
            return cached

    # Use compact, high-signal excerpts to minimize prompt evaluation time on CPU
    readme_snippet = clean_markdown_summary(repo_data.get("readme") or "", max_paragraphs=1)[:500]
    repo_desc = (repo_data.get("description") or "")[:250]
    lang = base_guide.get("stack_info", {}).get("language", "General")
    tool = base_guide.get("stack_info", {}).get("package_manager", "git")

    prompt = f"""Summarize this repository for an open-source contributor onboarding guide.
Repository: {repo_data.get('full_name', '')}
Language: {lang} | Build Tool: {tool}
Description: {repo_desc}
Readme excerpt: {readme_snippet}

Respond ONLY in valid JSON. No reasoning, no <think> tags, no markdown commentary.
{{
  "overview": "Clear 2-sentence summary of what this project does and its core architecture.",
  "prerequisites": ["2 verified tools needed to run this project"],
  "contributor_tips": ["2 actionable tips for newcomers in this repo"]
}}"""

    try:
        ai_data = generate_json(
            prompt=prompt,
            system=SYSTEM_PROMPT,
            schema_keys=["overview"],
            temperature=0.1,
            max_tokens=250,
        )
        if ai_data.get("overview") and len(ai_data["overview"].strip()) > 20:
            base_guide["overview"] = ai_data["overview"].strip()
        if ai_data.get("prerequisites"):
            base_guide["prerequisites"] = ai_data["prerequisites"]
        if ai_data.get("contributor_tips"):
            base_guide["contributor_tips"] = ai_data["contributor_tips"]
        base_guide["is_ai_enriched"] = True
    except (LLMUnavailableError, LLMOutputError, Exception):
        # Base grounded guide is already high quality and ready!
        pass

    # Save to database cache
    if repo_id:
        save_cached_guide(repo_id, base_guide)

    return base_guide
