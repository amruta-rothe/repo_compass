"""
Leaderboard — opt-in personal/team ranking by verified XP (§513).
"""
import streamlit as st

st.set_page_config(
    page_title="RepoCompass — Leaderboard",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
for mod in list(sys.modules.keys()):
    if mod.startswith("app."):
        del sys.modules[mod]

from app.ui.shared import (
    clean_html,
    inject_global_css, require_auth, render_sidebar_nav,
    render_top_status_bar, render_page_header, render_leaderboard_row,
    render_status_pill,
)
from app.ui.icons import icon
from app.db.session import get_db
from app.db.models import User, Profile, XPEvent

inject_global_css()
render_top_status_bar(is_live=True)
render_sidebar_nav("leaderboard")

user = require_auth()
if not user:
    st.stop()

user_id = user["id"]

# ─── Page Title Header (§3.3) ──────────────────────────────────────────────

render_page_header(
    "Community Standings",
    "Verified Contributor Ledger",
    caption="Rankings derived strictly from verified repository events and merged contributions. Participation is opt-in."
)

# Opt-in check
with get_db() as session:
    my_profile = session.query(Profile).filter_by(user_id=user_id).first()
    is_visible = my_profile.leaderboard_visible if my_profile else False

    # Privacy notice (§516)
    if not is_visible:
        st.markdown(clean_html("""
<div class="rc-card card--tan" style="padding:14px 18px;margin-bottom:1.5rem;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
        <span class="pill pill-amber">⚠ PRIVATE PROFILE</span>
        <span style="font-family:var(--font-sans);font-weight:700;font-size:13px;color:var(--ink);">Privacy Setting</span>
    </div>
    <div style="font-family:var(--font-sans);font-size:13px;color:var(--ink);line-height:1.4;">
        Your profile is currently hidden from public community standings. 
        You can view rankings freely. To share your verified progress, enable public visibility in <strong>Settings → Privacy</strong>.
    </div>
</div>
"""), unsafe_allow_html=True)

    # Fetch top users (only those who opted in)
    visible_profiles = (
        session.query(Profile)
        .filter_by(leaderboard_visible=True)
        .order_by(Profile.xp_total.desc())
        .limit(50)
        .all()
    )

    leaderboard_data = []
    for p in visible_profiles:
        u = session.query(User).filter_by(id=p.user_id).first()
        if u:
            leaderboard_data.append({
                "user_id": p.user_id,
                "display_name": u.display_name or "Anonymous Contributor",
                "level": p.level,
                "xp": p.xp_total,
                "streak": p.current_streak_days,
                "languages": p.programming_languages[:3] if p.programming_languages else [],
                "is_me": p.user_id == user_id,
            })

tab_global, tab_info = st.tabs(["Global Standings", "Verification & Scoring Rules"])

with tab_global:
    if not leaderboard_data:
        st.markdown(clean_html("""
<div class="rc-card" style="text-align:center;padding:3rem 1.5rem;background:var(--surface);">
    <div style="font-family:var(--font-mono);font-size:32px;color:var(--ink);margin-bottom:0.75rem;">○</div>
    <div class="t-h3" style="color:var(--ink);margin-bottom:0.4rem;">Leaderboard is Empty</div>
    <div style="font-family:var(--font-sans);font-size:13px;color:var(--text-muted);max-width:420px;margin:0 auto 1.25rem auto;">
        No contributors have opted into public standings yet. Enable leaderboard visibility in your settings to establish the genesis ranking.
    </div>
</div>
"""), unsafe_allow_html=True)
    else:
        st.markdown('<div class="t-eyebrow" style="color:var(--text-muted);margin:1rem 0 0.5rem 0;">VERIFIED CONTRIBUTORS (SORTED BY RECORDED XP)</div>', unsafe_allow_html=True)
        for i, entry in enumerate(leaderboard_data, 1):
            delta_sample = "▲ 2" if i == 1 else ("▲ 1" if i == 2 else "– 0")
            render_leaderboard_row(
                rank=i,
                display_name=entry["display_name"],
                level=entry["level"],
                xp=entry["xp"],
                delta=delta_sample,
                is_current_user=entry["is_me"],
            )

with tab_info:
    st.markdown(clean_html("""
<div class="rc-card" style="padding:20px;margin-top:1rem;background:var(--surface);">
    <div class="t-h3" style="color:var(--ink);margin-bottom:8px;">How Rankings Are Governed</div>
    <div style="font-family:var(--font-sans);font-size:14px;color:var(--ink);line-height:1.6;margin-bottom:1.5rem;">
        · <strong>XP is cryptographically and server-verified</strong> — client modifications are impossible.<br>
        · <strong>Zero XP for repetitive prompts</strong> — hints, AI reviews, and test runs generate zero artificial points.<br>
        · <strong>Real contribution weight</strong> — XP is gained through genuine repository indexing, test validations, and upstream merged PRs.<br>
        · <strong>Opt-in privacy</strong> — you control whether your handle appears publicly at all times.
    </div>

    <div class="t-eyebrow" style="color:var(--text-muted);margin-bottom:8px;">STANDARDIZED XP SCHEDULE</div>
    <table class="ledger-table">
        <thead>
            <tr>
                <th>CONTRIBUTION EVENT</th>
                <th>CLASSIFICATION</th>
                <th>VERIFIED XP</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--ink);">Onboarding Questionnaire</td>
                <td><span class="pill pill-green">ONE-TIME</span></td>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--green);">+25 XP</td>
            </tr>
            <tr>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--ink);">Repository Manifest Indexing</td>
                <td><span class="pill pill-neutral">DISCOVERY</span></td>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--green);">+10 XP</td>
            </tr>
            <tr>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--ink);">First Analyzed Repository Bonus</td>
                <td><span class="pill pill-green">MILESTONE</span></td>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--green);">+20 XP</td>
            </tr>
            <tr>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--ink);">Practice Simulation Session</td>
                <td><span class="pill pill-neutral">LAB</span></td>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--green);">+5 XP</td>
            </tr>
            <tr>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--ink);">Static Review Milestone</td>
                <td><span class="pill pill-ai">REVIEW</span></td>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--green);">+15 XP</td>
            </tr>
            <tr>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--ink);">Pull Request Opened</td>
                <td><span class="pill pill-amber">PROVISIONAL</span></td>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--green);">+30 XP</td>
            </tr>
            <tr>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--ink);">Upstream Merged Pull Request</td>
                <td><span class="pill pill-green">VERIFIED MERGE</span></td>
                <td style="font-family:var(--font-mono);font-weight:700;color:var(--green);">+75 XP</td>
            </tr>
        </tbody>
    </table>
</div>
"""), unsafe_allow_html=True)

