"""
Sakura Trail Arcade — 3D Gamified Navigator for RepoCompass.
Drive the Cyber-Sakura Rover across the valley to enter any dashboard section.
Full mobile touch support, procedural textures, spatial audio, and Torii gates.
"""
import os
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="RepoCompass — 3D Sakura Trail Arcade",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

import sys
for mod in list(sys.modules.keys()):
    if mod.startswith("app."):
        del sys.modules[mod]

from app.ui.shared import (
    inject_global_css, render_sidebar_nav, get_current_user,
    render_top_status_bar, render_page_header, clean_html,
)
from app.ui.icons import icon

inject_global_css()
render_top_status_bar(is_live=True)
render_sidebar_nav("sakura_trail")

# Load the enhanced 3D HTML file
html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "RepoCompass — Sakura Trail.html")
with open(html_path, "r", encoding="utf-8") as f:
    sakura_html = f.read()

# ─── Page Title Header (§3.3) ──────────────────────────────────────────────

render_page_header(
    "Sakura Trail Arcade",
    "3D Spatial Navigator",
    caption="Drive the Cyber-Sakura Rover across the valley to enter Torii gates and explore repository intelligence."
)

# Quick Navigation Shortcuts for Judges / Fast Access
with st.expander("Fast-Travel Gate Shortcuts (Click to jump immediately)", expanded=False):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        if st.button("Discover", use_container_width=True, key="quick_explore"):
            st.switch_page("pages/03_explore.py")
    with c2:
        if st.button("Learn", use_container_width=True, key="quick_learn"):
            st.switch_page("pages/04_learning.py")
    with c3:
        if st.button("Practice", use_container_width=True, key="quick_practice"):
            st.switch_page("pages/05_practice.py")
    with c4:
        if st.button("Maintain", use_container_width=True, key="quick_maintainer"):
            st.switch_page("pages/07_maintainer.py")
    with c5:
        if st.button("Hall of Fame", use_container_width=True, key="quick_leaderboard"):
            st.switch_page("pages/06_leaderboard.py")
    with c6:
        if st.button("Dashboard", use_container_width=True, key="quick_dashboard"):
            st.switch_page("pages/02_dashboard.py")

# Embed the interactive 3D WebGL Canvas — styled with Solo Ledger border
st.markdown("""
<style>
iframe[title="streamlit_components.v1.components.html"] {
    border: 2px solid var(--ink) !important;
    border-radius: var(--radius-card) !important;
    background: var(--navy) !important;
}
</style>
""", unsafe_allow_html=True)
components.html(sakura_html, height=780, scrolling=False)

st.markdown(clean_html("""
<div class="rc-card" style="text-align:center;padding:12px 16px;margin-top:0.75rem;">
    <div style="font-family:var(--font-mono);font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:var(--text-muted);">
        <span style="color:var(--ink);font-weight:700;">Keyboard:</span>
        <code style="background:var(--canvas);border:1px solid var(--rule);border-radius:4px;padding:1px 5px;margin:0 2px;">W A S D</code> or
        <code style="background:var(--canvas);border:1px solid var(--rule);border-radius:4px;padding:1px 5px;margin:0 2px;">Arrow Keys</code> to drive ·
        <code style="background:var(--canvas);border:1px solid var(--rule);border-radius:4px;padding:1px 5px;margin:0 2px;">Shift</code> for Nitro ·
        <code style="background:var(--canvas);border:1px solid var(--rule);border-radius:4px;padding:1px 5px;margin:0 2px;">Enter</code> to launch gate
        &nbsp;│&nbsp;
        <span style="color:var(--ink);font-weight:700;">Mobile:</span> Virtual joystick + touch buttons
    </div>
</div>
"""), unsafe_allow_html=True)
