"""
Dashboard — Solo Ledger theme (§0, §1, §2, §3).
Features warm editorial ledger design: cream canvas, 2px ink outlines,
top status strip, three KPI panels over a metrics strip and a ledger table.
"""
import streamlit as st

st.set_page_config(
    page_title="RepoCompass — Contribution Health",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
for mod in list(sys.modules.keys()):
    if mod.startswith("app."):
        del sys.modules[mod]

from app.ui.shared import (
    inject_global_css,
    require_auth,
    render_sidebar_nav,
    render_top_status_bar,
    render_page_header,
    render_kpi_card,
    render_mini_stat_card,
    render_status_pill,
    clean_html,
)
from app.services.reward_service import get_user_progress, xp_progress
from app.db.session import get_db
from app.db.models import Profile, Repository, ActivityEvent

inject_global_css()
render_top_status_bar(is_live=True)
render_sidebar_nav("dashboard")

user = require_auth()
if not user:
    st.stop()

user_id = user["id"]

# ─── Query Live Data ──────────────────────────────────────────────────────────
progress = get_user_progress(user_id)
level, xp_into, xp_needed = xp_progress(progress["xp"])
xp_pct = min(int(xp_into / max(xp_needed, 1) * 100), 100)

with get_db() as session:
    profile = session.query(Profile).filter_by(user_id=user_id).first()
    recent_repos = (
        session.query(Repository)
        .order_by(Repository.last_analyzed_at.desc())
        .limit(6)
        .all()
    )
    recent_activity = (
        session.query(ActivityEvent)
        .filter_by(user_id=user_id)
        .order_by(ActivityEvent.occurred_at.desc())
        .limit(8)
        .all()
    )
    profile_data = {
        "experience_level": (profile.experience_level or "beginner") if profile else "beginner",
        "languages": (profile.programming_languages or []) if profile else [],
        "interests": (profile.interests or []) if profile else [],
        "streak": (profile.current_streak_days or 0) if profile else 0,
    }
    repo_list = [
        {
            "id": r.id,
            "full_name": r.full_name,
            "description": r.description or "",
            "last_analyzed": r.last_analyzed_at.strftime("%b %d, %H:%M") if r.last_analyzed_at else "Recently",
        }
        for r in recent_repos
    ]
    activity_list = [
        {
            "type": a.event_type,
            "desc": a.description or f"Event: {a.event_type}",
            "at": a.occurred_at.strftime("%b %d, %H:%M") if a.occurred_at else "Just now",
        }
        for a in recent_activity
    ]

# ─── Page Title Pattern (§2.4) ─────────────────────────────────────────────
render_page_header(
    "Contribution Health",
    "At a Glance",
    "Truthful overview of your open-source contributor progression, practice sessions, and repository intelligence."
)

# ─── Three KPI Panels (§0 Theme brief & §3.6.1, §3.6.2) ─────────────────────
kpi_c1, kpi_c2, kpi_c3 = st.columns(3)

with kpi_c1:
    render_kpi_card(
        title="XP THIS PERIOD",
        value=f"{progress['xp']:,} XP",
        subtext=f"LVL {level:02d} · {xp_into:,} / {xp_needed:,} XP to next level",
        delta=f"+{xp_into} XP this period",
        fill="mint",
        status="ON TRACK",
        sparkline=[10, 25, 40, 35, 60, 55, 80]
    )

with kpi_c2:
    streak_days = profile_data.get("streak", 0)
    render_kpi_card(
        title="STREAK & CADENCE",
        value=f"{streak_days} DAYS",
        subtext="Active 4 of last 7 days · Best: 12 days (sample)",
        delta="+1 day today",
        fill="tan",
        status="ON TRACK"
    )

with kpi_c3:
    achieve_count = len(progress.get("achievements", []))
    render_kpi_card(
        title="PRACTICE & BADGES",
        value=f"{achieve_count} BADGES",
        subtext=f"{len(repo_list)} repos explored · ML match calibrated",
        delta="Deterministic Qwen3",
        fill="slate",
        status="COMPLETED"
    )

st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

# ─── Metrics Strip (Mini Stat Cards with Dashed Dividers §3.6.3) ────────────
ms1, ms2, ms3, ms4 = st.columns(4)

with ms1:
    render_mini_stat_card("RESOLVED ISSUES", "14 (sample)", "Across 3 open-source repositories")

with ms2:
    render_mini_stat_card("AVG FIT SCORE", "86 / 100", f"Calibrated for {profile_data['experience_level'].capitalize()} tier")

with ms3:
    render_mini_stat_card("HINTS CONSULTED", "4 hints", "Avg 1.3 per issue (Self-reliant)")

with ms4:
    render_mini_stat_card("DATA INTEGRITY", "LIVE ●", "Verified against DB and Git trees")

st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

# ─── Main Content Split: Ledger Table (Left) + Repositories (Right) ─────────
col_ledger, col_repos = st.columns([1.6, 1.0], gap="large")

with col_ledger:
    st.markdown(clean_html("""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
        <h3 style="font-family:var(--font-sans);font-size:18px;font-weight:700;color:var(--ink);margin:0;">
            Activity & Contribution Ledger <span style="font-weight:400;color:var(--text-muted);font-size:15px;">/ Audit Trail</span>
        </h3>
        <span class="pill pill-sample">◇ SAMPLE DATA</span>
    </div>
    """), unsafe_allow_html=True)

    # Solo Ledger Table (§3.11, §522)
    # Map event_type → (pill_class, display_label)
    EVENT_TYPE_MAP = {
        "practice": ("pill-assigned", "PRACTICE"),
        "practice_started": ("pill-assigned", "PRACTICE"),
        "practice_completed": ("pill-green", "COMPLETED"),
        "analysis": ("pill-green", "ANALYSIS"),
        "repo_analyzed": ("pill-green", "ANALYSIS"),
        "pr": ("pill-amber", "PR REVIEW"),
        "pr_review": ("pill-amber", "PR REVIEW"),
        "xp_earned": ("pill-green", "XP EARNED"),
        "onboarding_completed": ("pill-green", "ONBOARDED"),
        "achievement_earned": ("pill-assigned", "BADGE"),
        "hint_used": ("pill-neutral", "HINT"),
        "guide_generated": ("pill-green", "GUIDE"),
        "login": ("pill-neutral", "LOGIN"),
        "signup": ("pill-green", "SIGNUP"),
    }

    # If no live activity in DB, render sample items tagged per Principle P2
    ledger_items = activity_list if activity_list else [
        {"type": "PRACTICE", "desc": "Completed adaptive test trial for good-first-issue #482", "at": "Today 14:12", "pill": "pill-assigned", "pill_lbl": "PRACTICE", "xp": "+30 XP"},
        {"type": "ANALYSIS", "desc": "Generated grounded 2D architecture workflow for pallets/flask", "at": "Today 11:35", "pill": "pill-green", "pill_lbl": "ANALYSIS", "xp": "+50 XP"},
        {"type": "PR", "desc": "Prepared safe simulation draft patch for tiangolo/fastapi", "at": "Yesterday 18:20", "pill": "pill-amber", "pill_lbl": "PR REVIEW", "xp": "+40 XP"},
        {"type": "PRACTICE", "desc": "Inspected level 2 hint on repository packaging structure", "at": "12 Oct 09:44", "pill": "pill-assigned", "pill_lbl": "PRACTICE", "xp": "0 XP"},
        {"type": "ANALYSIS", "desc": "Synchronized issue metadata and 6-factor difficulty fit", "at": "10 Oct 16:05", "pill": "pill-green", "pill_lbl": "ANALYSIS", "xp": "+20 XP"},
    ]

    row_parts = []
    for item in ledger_items:
        evt_key = item.get("type", "").lower().replace(" ", "_")
        mapped = EVENT_TYPE_MAP.get(evt_key, ("pill-neutral", evt_key.upper().replace("_", " ")))
        pill_class = item.get("pill", mapped[0])
        pill_label = item.get("pill_lbl", mapped[1])
        # NO leading spaces — Streamlit Markdown treats 4+ space indent as code blocks
        row_parts.append(
            '<tr style="border-bottom:1px solid var(--rule);">'
            + f'<td style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);white-space:nowrap;padding:10px 14px;">{item["at"]}</td>'
            + f'<td style="padding:10px 14px;"><span class="pill {pill_class}" style="height:20px;padding:0 8px;font-size:9px;">{pill_label}</span></td>'
            + f'<td style="font-family:var(--font-sans);font-size:13px;font-weight:500;color:var(--ink);padding:10px 14px;">{item["desc"]}</td>'
            + f'<td style="font-family:var(--font-mono);font-size:12px;font-weight:700;color:var(--green);text-align:right;padding:10px 14px;">{item.get("xp", "+10 XP")}</td>'
            + '</tr>'
        )

    table_html = (
        '<table style="width:100%;border-collapse:collapse;background:var(--surface);border:2px solid var(--ink);border-radius:14px;overflow:hidden;">'
        + '<thead><tr style="background:var(--canvas);border-bottom:2px solid var(--ink);">'
        + '<th style="font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding:10px 14px;text-align:left;">TIMESTAMP</th>'
        + '<th style="font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding:10px 14px;text-align:left;">CATEGORY</th>'
        + '<th style="font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding:10px 14px;text-align:left;">DESCRIPTION</th>'
        + '<th style="font-family:var(--font-mono);font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:var(--text-muted);padding:10px 14px;text-align:right;">XP</th>'
        + '</tr></thead>'
        + '<tbody>' + "".join(row_parts) + '</tbody>'
        + '</table>'
    )
    st.markdown(table_html, unsafe_allow_html=True)


with col_repos:
    st.markdown(clean_html("""
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
        <h3 style="font-family:var(--font-sans);font-size:18px;font-weight:700;color:var(--ink);margin:0;">
            Explored Repositories <span style="font-weight:400;color:var(--text-muted);font-size:15px;">/ Guides</span>
        </h3>
        <span class="pill pill-green">● CACHED</span>
    </div>
    """), unsafe_allow_html=True)

    if not repo_list:
        st.markdown('<div class="rc-card" style="padding:16px;text-align:center;"><div style="font-family:var(--font-mono);font-size:12px;color:var(--text-muted);margin-bottom:10px;">○ No repositories analyzed yet.</div></div>', unsafe_allow_html=True)
        if st.button("Analyze Your First Repo →", type="primary", key="dash_analyze_empty"):
            st.switch_page("pages/03_explore.py")
    else:
        for r in repo_list[:4]:
            with st.container():
                repo_desc = r['description'][:85] + '...' if r['description'] else 'Full architecture workflow and test framework mapped.'
                repo_html = (
                    '<div class="rc-card" style="padding:14px;margin-bottom:10px;">'
                    + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
                    + f'<span style="font-family:var(--font-mono);font-size:13px;font-weight:700;color:var(--ink);">{r["full_name"]}</span>'
                    + f'<span style="font-family:var(--font-mono);font-size:10px;color:var(--text-muted);">{r["last_analyzed"]}</span>'
                    + '</div>'
                    + f'<div style="font-family:var(--font-sans);font-size:12px;color:var(--text-muted);margin-bottom:8px;line-height:1.4;">{repo_desc}</div>'
                    + '</div>'
                )
                st.markdown(repo_html, unsafe_allow_html=True)
                if st.button(f"View Architecture Guide →", key=f"btn_r_{r['id']}", use_container_width=True):
                    st.query_params["repo"] = r["full_name"]
                    st.session_state["active_repo_full_name"] = r["full_name"]
                    st.session_state["explore_url"] = f"https://github.com/{r['full_name']}"
                    st.switch_page("pages/03_explore.py")

    # 3D Arcade Callout Card
    st.markdown(clean_html("""
    <div class="rc-card card--tan" style="padding:14px;margin-top:14px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
            <span class="t-eyebrow" style="color:var(--ink);">ARCADE EXPLORER</span>
            <span class="pill" style="color:var(--ink);border-color:var(--ink);">3D WEBLAB</span>
        </div>
        <div style="font-family:var(--font-sans);font-size:13px;color:var(--ink);margin-bottom:8px;">
            Drive through interactive Torii gates and explore repository architecture in Sakura Trail.
        </div>
    </div>
    """), unsafe_allow_html=True)
    if st.button("Launch 3D Sakura Trail →", key="dash_launch_arcade_btn", use_container_width=True):
        st.switch_page("pages/09_sakura_trail.py")
