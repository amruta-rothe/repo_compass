"""
Unit tests for guide generator and dynamic workflow chart.
"""
from app.services.guide_generator import (
    detect_repository_stack,
    generate_grounded_guide,
    build_dynamic_workflow_steps,
    clean_markdown_summary,
)
from app.ui.workflow_chart import generate_mermaid_workflow, _get_svg_icon


def test_detect_python_poetry_stack():
    repo_data = {
        "primary_language": "Python",
        "full_name": "psf/black",
        "dep_files": {
            "pyproject.toml": "[tool.poetry]\nname = 'black'\n[tool.poetry.dependencies]\npytest = '^7.0'",
        },
        "tree": [{"path": "pyproject.toml", "type": "blob"}, {"path": "src/black/__init__.py", "type": "blob"}],
    }
    stack = detect_repository_stack(repo_data)
    assert stack["language"] == "Python"
    assert stack["package_manager"] == "Poetry"
    assert "poetry install" in stack["install_command"]
    assert "pytest" in stack["test_command"]


def test_detect_node_stack():
    repo_data = {
        "primary_language": "TypeScript",
        "full_name": "facebook/react",
        "dep_files": {
            "package.json": '{"scripts": {"test": "jest"}, "dependencies": {"react": "^18.0.0"}}',
        },
        "tree": [{"path": "package.json", "type": "blob"}],
    }
    stack = detect_repository_stack(repo_data)
    assert stack["language"] == "TypeScript"
    assert stack["package_manager"] == "npm"
    assert stack["install_command"] == "npm install"


def test_generate_grounded_guide_and_workflow():
    repo_data = {
        "full_name": "tiangolo/fastapi",
        "primary_language": "Python",
        "description": "FastAPI framework, high performance, easy to learn, fast to code, ready for production",
        "readme": "# FastAPI\n\nFastAPI framework is a modern, fast (high-performance) web framework for building APIs with Python.\n\n## Requirements\n\nPython 3.8+",
        "contributing": "# Contributing to FastAPI\n\nThanks for your interest in contributing to FastAPI!",
        "tree": [
            {"path": "fastapi/__init__.py", "type": "blob"},
            {"path": "tests/test_main.py", "type": "blob"},
            {"path": "docs/index.md", "type": "blob"},
        ],
        "dep_files": {
            "pyproject.toml": "[tool.poetry]\nname = 'fastapi'",
        },
    }
    guide = generate_grounded_guide(repo_data)
    assert "FastAPI" in guide["overview"]
    assert len(guide["tech_stack"]) > 0
    assert len(guide["setup_steps"]) >= 3
    assert len(guide["contribution_workflow"]) == 5

    # Check workflow steps match the 5 milestone colors and icons
    wf = guide["contribution_workflow"]
    assert wf[0]["color"] == "#10B981"
    assert wf[0]["icon_type"] == "target"
    assert wf[1]["color"] == "#F59E0B"
    assert wf[1]["icon_type"] == "magnifier"
    assert wf[2]["color"] == "#2563EB"
    assert wf[2]["icon_type"] == "branch"
    assert wf[3]["color"] == "#10B981"
    assert wf[3]["icon_type"] == "pencil"
    assert wf[4]["color"] == "#F59E0B"
    assert wf[4]["icon_type"] == "eye"

    # Test mermaid generation
    mermaid = generate_mermaid_workflow(wf)
    assert "graph TD" in mermaid
    assert "S1" in mermaid
    assert "S5" in mermaid


def test_clean_markdown_summary():
    raw_md = """
    # Project Title
    [![Build Status](https://img.shields.io/badge/build-passing-green.svg)](https://example.com)
    [![Coverage](https://codecov.io/gh/repo/branch/graph/badge.svg)](https://example.com)

    This is the first real substantive paragraph describing what this repository does. It contains useful explanation for contributors.

    | Column 1 | Column 2 |
    | --- | --- |
    | val | val |

    And here is another substantive paragraph that explains the architecture and design goals of the system.
    """
    clean = clean_markdown_summary(raw_md)
    assert "shields.io" not in clean
    assert "Build Status" not in clean
    assert "Column 1" not in clean
    assert "first real substantive paragraph" in clean
