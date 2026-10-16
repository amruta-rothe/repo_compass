"""
Dynamic 2D Workflow Chart Component for RepoCompass.
Renders an infographic-grade 2D contribution roadmap modeled directly on
the user's reference design:
  - Central vertical milestone axis
  - Alternating cards (Emerald Green #10B981, Amber #F59E0B, Royal Blue #2563EB)
  - Custom vector iconography (Target/Bullseye, Magnifier, Flowchart, Pencil, Eye)
  - Copyable shell commands tailored to the repository's detected stack
  - Responsive desktop & mobile layout
  - Mermaid flowchart view for interactive diagramming
"""
from __future__ import annotations

import html
from typing import Any, Dict, List
import streamlit as st
from app.ui.icons import icon


def _get_svg_icon(icon_type: str, color: str = "#101B35") -> str:
    """Returns crisp inline vector art matching the user's reference infographic."""
    if icon_type == "target":
        # Target / Bullseye (Step 1)
        return f"""
        <svg width="84" height="84" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="50" cy="50" r="42" stroke="{color}" stroke-width="4" stroke-dasharray="2 0" opacity="0.85"/>
            <circle cx="50" cy="50" r="30" stroke="{color}" stroke-width="4"/>
            <circle cx="50" cy="50" r="18" fill="#10B981" stroke="{color}" stroke-width="3"/>
            <circle cx="50" cy="50" r="7" fill="white"/>
            <line x1="50" y1="2" x2="50" y2="18" stroke="{color}" stroke-width="4" stroke-linecap="round"/>
            <line x1="50" y1="82" x2="50" y2="98" stroke="{color}" stroke-width="4" stroke-linecap="round"/>
            <line x1="2" y1="50" x2="18" y2="50" stroke="{color}" stroke-width="4" stroke-linecap="round"/>
            <line x1="82" y1="50" x2="98" y2="50" stroke="{color}" stroke-width="4" stroke-linecap="round"/>
        </svg>
        """
    elif icon_type == "magnifier":
        # Magnifying Glass (Step 2)
        return f"""
        <svg width="84" height="84" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <circle cx="42" cy="42" r="30" stroke="{color}" stroke-width="5" fill="white" fill-opacity="0.9"/>
            <path d="M26 30 C30 22, 42 20, 52 24" stroke="#F59E0B" stroke-width="4" stroke-linecap="round" fill="none"/>
            <line x1="64" y1="64" x2="92" y2="92" stroke="{color}" stroke-width="8" stroke-linecap="round"/>
            <circle cx="42" cy="42" r="14" stroke="#F59E0B" stroke-width="2" stroke-dasharray="4 4" fill="none"/>
        </svg>
        """
    elif icon_type == "branch":
        # Flowchart / Branch Diagram (Step 3)
        return f"""
        <svg width="84" height="84" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="6" y="8" width="88" height="84" rx="8" fill="white" stroke="{color}" stroke-width="3" opacity="0.95"/>
            <rect x="16" y="20" width="28" height="18" rx="4" fill="#F59E0B"/>
            <rect x="16" y="56" width="28" height="24" rx="4" fill="#2563EB" transform="rotate(45 30 68)"/>
            <rect x="56" y="38" width="30" height="16" rx="8" fill="#101B35"/>
            <line x1="44" y1="29" x2="56" y2="46" stroke="{color}" stroke-width="3"/>
            <line x1="44" y1="68" x2="56" y2="46" stroke="{color}" stroke-width="3"/>
            <line x1="56" y1="68" x2="80" y2="68" stroke="#2563EB" stroke-width="4" stroke-linecap="round"/>
            <line x1="56" y1="76" x2="74" y2="76" stroke="#2563EB" stroke-width="4" stroke-linecap="round"/>
        </svg>
        """
    elif icon_type == "pencil":
        # Pencil / Code Editor (Step 4)
        return f"""
        <svg width="84" height="84" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <g transform="rotate(-45 50 50)">
                <rect x="36" y="10" width="28" height="58" rx="4" fill="#101B35" stroke="white" stroke-width="2"/>
                <rect x="42" y="10" width="16" height="58" fill="#F59E0B"/>
                <polygon points="36,68 64,68 50,92" fill="#101B35"/>
                <polygon points="46,84 54,84 50,92" fill="#F59E0B"/>
                <rect x="36" y="6" width="28" height="8" rx="2" fill="#C94C4C"/>
            </g>
            <path d="M15 82 C35 78, 55 92, 85 84" stroke="{color}" stroke-width="4" stroke-linecap="round" fill="none"/>
        </svg>
        """
    elif icon_type == "eye":
        # Eye / Review (Step 5)
        return f"""
        <svg width="84" height="84" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M10 50 C25 22, 75 22, 90 50 C75 78, 25 78, 10 50 Z" fill="white" stroke="{color}" stroke-width="4"/>
            <circle cx="50" cy="50" r="18" fill="#101B35"/>
            <circle cx="50" cy="50" r="9" fill="#F59E0B"/>
            <circle cx="47" cy="47" r="4" fill="white"/>
            <!-- Lashes -->
            <line x1="18" y1="26" x2="12" y2="16" stroke="{color}" stroke-width="3" stroke-linecap="round"/>
            <line x1="38" y1="18" x2="34" y2="8" stroke="{color}" stroke-width="3" stroke-linecap="round"/>
            <line x1="62" y1="18" x2="66" y2="8" stroke="{color}" stroke-width="3" stroke-linecap="round"/>
            <line x1="82" y1="26" x2="88" y2="16" stroke="{color}" stroke-width="3" stroke-linecap="round"/>
        </svg>
        """
    return ""


def render_workflow_infographic(steps: List[Dict[str, Any]], repo_name: str):
    """
    Renders the modern, clean 2D workflow chart directly inspired by the user's reference image.
    """
    card_html_items = []

    for step in steps:
        num = step.get("step_number", 1)
        title = html.escape(step.get("title", ""))
        directive = html.escape(step.get("directive", ""))
        cmd = html.escape(step.get("command", "") or "")
        bg_color = step.get("color", "#10B981")
        icon_type = step.get("icon_type", "target")
        icon_pos = step.get("icon_position", "left")
        source = html.escape(step.get("source", "Repository Analysis"))

        svg_code = _get_svg_icon(icon_type, color="#101B35")

        cmd_block = f"""
        <div class="wf-code-box">
            <code>{cmd}</code>
        </div>
        """ if cmd else ""

        # Left or Right icon positioning
        if icon_pos == "left":
            row_content = f"""
            <div class="wf-row wf-row-left">
                <div class="wf-icon-slot wf-icon-left">
                    {svg_code}
                </div>
                <div class="wf-card" style="background: {bg_color};">
                    <div class="wf-step-num">{num}.</div>
                    <div class="wf-card-title">{title}</div>
                    <div class="wf-card-body">{directive}</div>
                    {cmd_block}
                    <div class="wf-source-tag">{icon('tag', 12, '#6B7280')} {source}</div>
                </div>
                <div class="wf-icon-placeholder"></div>
            </div>
            """
        else:
            row_content = f"""
            <div class="wf-row wf-row-right">
                <div class="wf-icon-placeholder"></div>
                <div class="wf-card" style="background: {bg_color};">
                    <div class="wf-step-num">{num}.</div>
                    <div class="wf-card-title">{title}</div>
                    <div class="wf-card-body">{directive}</div>
                    {cmd_block}
                    <div class="wf-source-tag">{icon('tag', 12, '#6B7280')} {source}</div>
                </div>
                <div class="wf-icon-slot wf-icon-right">
                    {svg_code}
                </div>
            </div>
            """
        card_html_items.append(row_content)

    cards_joined = "\n".join(card_html_items)

    full_html = f"""
    <style>
    .wf-container {{
        position: relative;
        max-width: 820px;
        margin: 2rem auto;
        padding: 2.5rem 1rem 3rem 1rem;
        background: #F8FAFC;
        border: 1px solid rgba(107, 120, 144, 0.15);
        border-radius: 24px;
        box-shadow: 0 10px 30px rgba(16, 27, 53, 0.04);
        font-family: 'Inter', -apple-system, sans-serif;
    }}
    .wf-header {{
        text-align: center;
        margin-bottom: 2.5rem;
    }}
    .wf-header h2 {{
        font-size: 1.85rem;
        font-weight: 900;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #101B35;
        margin: 0 0 0.4rem 0;
    }}
    .wf-header p {{
        font-size: 0.95rem;
        color: #6B7890;
        margin: 0;
    }}
    /* Central Spine / Connector Pipe */
    .wf-timeline {{
        position: relative;
    }}
    .wf-timeline::before {{
        content: '';
        position: absolute;
        top: 30px;
        bottom: 30px;
        left: 50%;
        width: 8px;
        background: #F59E0B;
        transform: translateX(-50%);
        border-radius: 4px;
        z-index: 1;
    }}
    .wf-row {{
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
        margin-bottom: 2.5rem;
        z-index: 2;
    }}
    .wf-card {{
        flex: 0 1 540px;
        border-radius: 18px;
        padding: 1.75rem 2rem;
        color: white;
        box-shadow: 0 12px 28px -6px rgba(16, 27, 53, 0.18);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    .wf-card:hover {{
        transform: translateY(-2px);
        box-shadow: 0 16px 36px -6px rgba(16, 27, 53, 0.24);
    }}
    .wf-step-num {{
        font-size: 2.6rem;
        font-weight: 900;
        line-height: 1;
        margin-bottom: 0.4rem;
        color: rgba(255, 255, 255, 0.95);
        letter-spacing: -0.02em;
    }}
    .wf-card-title {{
        font-size: 1.15rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        color: #FFFFFF;
        letter-spacing: 0.01em;
    }}
    .wf-card-body {{
        font-size: 0.92rem;
        line-height: 1.55;
        color: rgba(255, 255, 255, 0.92);
        margin-bottom: 0.8rem;
    }}
    .wf-code-box {{
        background: rgba(16, 27, 53, 0.28);
        border: 1px solid rgba(255, 255, 255, 0.22);
        border-radius: 8px;
        padding: 0.65rem 0.9rem;
        margin-top: 0.75rem;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        color: #FFFFFF;
        white-space: pre-wrap;
        word-break: break-all;
        backdrop-filter: blur(4px);
    }}
    .wf-source-tag {{
        margin-top: 0.75rem;
        font-size: 0.72rem;
        color: rgba(255, 255, 255, 0.78);
        font-weight: 500;
    }}
    .wf-icon-slot {{
        flex: 0 0 110px;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .wf-icon-placeholder {{
        flex: 0 0 110px;
    }}
    @media (max-width: 768px) {{
        .wf-timeline::before {{
            left: 20px;
        }}
        .wf-row {{
            flex-direction: column;
            align-items: flex-start;
            gap: 0.8rem;
            padding-left: 45px;
        }}
        .wf-card {{
            width: 100%;
        }}
        .wf-icon-placeholder {{
            display: none;
        }}
        .wf-icon-slot {{
            align-self: flex-start;
        }}
    }}
    </style>

    <div class="wf-container">
        <div class="wf-header">
            <h2>HOW TO CONTRIBUTE</h2>
            <p>Visual 5-step workflow dynamically generated for <strong>{html.escape(repo_name)}</strong></p>
        </div>
        <div class="wf-timeline">
            {cards_joined}
        </div>
    </div>
    """

    st.markdown(full_html, unsafe_allow_html=True)


def generate_mermaid_workflow(steps: List[Dict[str, Any]]) -> str:
    """
    Renders an accessible Mermaid graph per PRD Section 5.4.
    """
    lines = ["graph TD"]
    lines.append('    classDef emerald fill:#10B981,stroke:#059669,stroke-width:2px,color:#fff,font-weight:bold;')
    lines.append('    classDef amber fill:#F59E0B,stroke:#D97706,stroke-width:2px,color:#fff,font-weight:bold;')
    lines.append('    classDef blue fill:#2563EB,stroke:#1D4ED8,stroke-width:2px,color:#fff,font-weight:bold;')

    prev_id = None
    for step in steps:
        s_id = f"S{step['step_number']}"
        title = step['title'].replace('"', "'")
        lines.append(f'    {s_id}["{step["step_number"]}. {title}"]')
        if prev_id:
            lines.append(f'    {prev_id} --> {s_id}')
        prev_id = s_id

        # Class
        color = step.get("color", "")
        if color == "#10B981":
            lines.append(f'    class {s_id} emerald;')
        elif color == "#F59E0B":
            lines.append(f'    class {s_id} amber;')
        else:
            lines.append(f'    class {s_id} blue;')

    return "\n".join(lines)
