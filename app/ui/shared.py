"""
Shared Streamlit UI utilities: theme, session state helpers, components.
"""
from __future__ import annotations

import streamlit as st
from typing import Optional
from app.ui.icons import icon


# ─── Design tokens (match PRD palette) ────────────────────────────────────

COLORS = {
    "ink": "#101B35",
    "dark_surface": "#172544",
    "teal": "#159A8C",
    "mint": "#DDF7F3",
    "light_bg": "#F7F9FC",
    "main_text": "#17243D",
    "muted": "#6B7890",
    "success": "#21866D",
    "warning": "#C8872D",
    "error": "#C94C4C",
    "ai": "#7565C7",
}


# ─── CSS ─────────────────────────────────────────────────────────────────

def inject_global_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Reset & base ──────────────────────────────────────────────────── */
html, body, [class*="css"], [data-testid="stAppViewContainer"], .stApp {
    font-family: 'Poppins', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    color: #111827;
}

.main .block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 1240px;
}

/* ── Sidebar (Clean Modern Style matching reference) ─────────────────── */
[data-testid="stSidebar"] {
    background: #0f172a !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
}

[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
    font-family: 'Poppins', sans-serif !important;
}

[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: #94a3b8 !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    padding: 0.55rem 0.9rem !important;
    width: 100%;
    text-align: left;
    transition: all 0.2s ease;
    display: flex;
    align-items: center;
    gap: 8px;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255, 255, 255, 0.06) !important;
    color: #f8fafc !important;
    border-color: rgba(255, 255, 255, 0.1) !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.5rem 1.25rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(21,154,140,0.3) !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 16px rgba(21,154,140,0.4) !important;
    transform: translateY(-1px) !important;
}

.stButton > button[kind="secondary"] {
    background: rgba(21,154,140,0.08) !important;
    color: #159A8C !important;
    border: 1px solid rgba(21,154,140,0.3) !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}

/* ── Cards ────────────────────────────────────────────────────────────── */
.rc-card {
    background: white;
    border: 1px solid rgba(107,120,144,0.15);
    border-radius: 12px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    transition: box-shadow 0.2s ease;
}

.rc-card:hover {
    box-shadow: 0 4px 16px rgba(16,27,53,0.08);
}

.rc-card-dark {
    background: linear-gradient(135deg, #101B35, #172544);
    border: 1px solid rgba(21,154,140,0.2);
    border-radius: 12px;
    padding: 1.25rem;
    color: #DDF7F3;
}

/* ── Badges ───────────────────────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}

.badge-beginner { background: rgba(33,134,109,0.12); color: #21866D; border: 1px solid rgba(33,134,109,0.25); }
.badge-intermediate { background: rgba(200,135,45,0.12); color: #C8872D; border: 1px solid rgba(200,135,45,0.25); }
.badge-advanced { background: rgba(201,76,76,0.12); color: #C94C4C; border: 1px solid rgba(201,76,76,0.25); }
.badge-ai { background: rgba(117,101,199,0.12); color: #7565C7; border: 1px solid rgba(117,101,199,0.25); }
.badge-teal { background: rgba(21,154,140,0.1); color: #159A8C; border: 1px solid rgba(21,154,140,0.25); }

/* ── Progress bar ─────────────────────────────────────────────────────── */
.xp-bar-container {
    background: rgba(107,120,144,0.12);
    border-radius: 99px;
    height: 8px;
    overflow: hidden;
    margin: 0.5rem 0;
}

.xp-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #159A8C, #7565C7);
    border-radius: 99px;
    transition: width 0.6s ease;
}

/* ── Code / mono ──────────────────────────────────────────────────────── */
code, pre, .mono {
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Hint levels ─────────────────────────────────────────────────────── */
.hint-box {
    background: linear-gradient(135deg, rgba(117,101,199,0.08), rgba(21,154,140,0.05));
    border: 1px solid rgba(117,101,199,0.2);
    border-left: 3px solid #7565C7;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.25rem;
    margin: 0.75rem 0;
}

/* ── Alert boxes ─────────────────────────────────────────────────────── */
.alert-info {
    background: rgba(21,154,140,0.06);
    border: 1px solid rgba(21,154,140,0.2);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    color: #0d7a70;
    font-size: 0.875rem;
}

.alert-warning {
    background: rgba(200,135,45,0.06);
    border: 1px solid rgba(200,135,45,0.2);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    color: #a06b20;
    font-size: 0.875rem;
}

/* ── Section headings ─────────────────────────────────────────────────── */
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #17243D;
    margin: 1.5rem 0 0.75rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ── Divider ─────────────────────────────────────────────────────────── */
.rc-divider {
    border: none;
    border-top: 1px solid rgba(107,120,144,0.15);
    margin: 1.25rem 0;
}

/* ── Metrics ─────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: white;
    border: 1px solid rgba(107,120,144,0.12);
    border-radius: 10px;
    padding: 0.75rem 1rem;
}

/* ── Input fields ─────────────────────────────────────────────────────── */
.stTextInput > div > div > input, .stTextArea textarea {
    border-radius: 8px !important;
    border-color: rgba(107,120,144,0.25) !important;
    font-family: 'Inter', sans-serif !important;
}

.stTextInput > div > div > input:focus, .stTextArea textarea:focus {
    border-color: #159A8C !important;
    box-shadow: 0 0 0 2px rgba(21,154,140,0.15) !important;
}

/* ── Tabs ──────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab"] {
    font-weight: 500 !important;
    color: #6B7890 !important;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #159A8C !important;
}

/* ── Spinner ──────────────────────────────────────────────────────────── */
.stSpinner > div {
    border-color: #159A8C transparent transparent transparent !important;
}

/* ── Selectbox, multiselect ────────────────────────────────────────────── */
.stSelectbox > div > div, .stMultiSelect > div > div {
    border-radius: 8px !important;
}

/* ── Radio / checkbox ─────────────────────────────────────────────────── */
.stRadio label, .stCheckbox label {
    font-size: 0.9rem !important;
}
</style>
""", unsafe_allow_html=True)


# ─── Session state helpers ─────────────────────────────────────────────────

def get_current_user() -> Optional[dict]:
    """
    Returns the authenticated user dict.
    If session_state is reset (e.g. browser refresh / F5), automatically restores
    the user session from the persistent query param token and database.
    """
    user = st.session_state.get("user")
    if user:
        return user

    # Restore session from persistent query parameter token upon refresh
    token = st.query_params.get("session")
    if token:
        try:
            from app.core.security import verify_session_token
            user_id = verify_session_token(token)
            if user_id:
                from app.db.session import get_db
                from app.db.models import User, Profile
                with get_db() as session:
                    u = session.query(User).filter_by(id=user_id, is_active=True).first()
                    if u:
                        p = session.query(Profile).filter_by(user_id=u.id).first()
                        user_dict = {
                            "id": u.id,
                            "email": u.email,
                            "display_name": u.display_name,
                            "avatar_url": u.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={u.display_name}",
                            "level": p.level if p else 1,
                            "xp": p.xp_total if p else 0,
                            "experience_level": p.experience_level if p else "beginner",
                        }
                        st.session_state["user"] = user_dict
                        st.session_state["session_token"] = token
                        return user_dict
        except Exception:
            pass

    return None


def set_current_user(user_dict: dict, token: Optional[str] = None):
    """Stores the active user session in memory and in persistent query params."""
    st.session_state["user"] = user_dict
    if not token:
        from app.core.security import create_session_token
        token = create_session_token(user_dict["id"])
    st.session_state["session_token"] = token
    st.query_params["session"] = token


def clear_current_user():
    """Wipes the active user session and clears persistent query params."""
    st.session_state.pop("user", None)
    st.session_state.pop("session_token", None)
    st.session_state.pop("active_repo", None)
    st.session_state.pop("active_repo_full_name", None)
    st.session_state.pop("analysis_result", None)
    st.session_state.pop("guide_content", None)
    if "session" in st.query_params:
        del st.query_params["session"]
    if "repo" in st.query_params:
        del st.query_params["repo"]


def require_auth() -> Optional[dict]:
    """Returns user dict if authenticated, else redirects to auth page."""
    user = get_current_user()
    if not user:
        st.session_state["redirect_to"] = st.session_state.get("current_page", "dashboard")
        st.switch_page("pages/01_auth.py")
    return user


def get_active_repo() -> Optional[dict]:
    repo = st.session_state.get("active_repo")
    if repo:
        return repo
    repo_param = st.query_params.get("repo")
    if repo_param:
        return {"full_name": repo_param}
    return None


def set_active_repo(repo_data: dict):
    st.session_state["active_repo"] = repo_data
    full_name = repo_data.get("full_name")
    if full_name:
        st.session_state["active_repo_full_name"] = full_name
        st.query_params["repo"] = full_name


# ─── Reusable components ───────────────────────────────────────────────────

def render_level_badge(level: int, xp: int, xp_into: int, xp_needed: int):
    pct = min(int(xp_into / max(xp_needed, 1) * 100), 100)
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.75rem;padding:0.75rem;background:white;border-radius:10px;border:1px solid rgba(107,120,144,0.12);">
    <div style="width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#159A8C,#7565C7);display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:1rem;flex-shrink:0;">{level}</div>
    <div style="flex:1;min-width:0;">
        <div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#6B7890;margin-bottom:4px;">
            <span>Level {level}</span>
            <span>{xp:,} XP total</span>
        </div>
        <div class="xp-bar-container">
            <div class="xp-bar-fill" style="width:{pct}%;"></div>
        </div>
        <div style="font-size:0.72rem;color:#6B7890;margin-top:2px;">{xp_into}/{xp_needed} XP to next level</div>
    </div>
</div>
""", unsafe_allow_html=True)


def render_difficulty_badge(difficulty: str) -> str:
    classes = {
        "beginner": "badge-beginner",
        "intermediate": "badge-intermediate",
        "advanced": "badge-advanced",
        "unavailable": "badge",
    }
    labels = {
        "beginner": "Beginner",
        "intermediate": "Intermediate",
        "advanced": "Advanced",
        "unavailable": "May be taken",
    }
    cls = classes.get(difficulty, "badge")
    label = labels.get(difficulty, difficulty.capitalize())
    return f'<span class="badge {cls}">{label}</span>'


def render_issue_card(issue_data: dict, score: float, difficulty: str, on_select=None):
    """Render a single issue card. issue_data should be dict-like."""
    labels_html = " ".join(
        f'<span class="badge badge-teal" style="font-size:0.65rem">{l}</span>'
        for l in (issue_data.get("labels") or [])[:5]
    )
    assignee_note = (
        f'<span style="color:#C8872D;font-size:0.78rem;display:inline-flex;align-items:center;gap:4px;">{icon("alert_triangle", 13, "#C8872D")} Has assignees</span>'
        if issue_data.get("assignees")
        else '<span style="color:#6B7890;font-size:0.78rem;">No assignee listed</span>'
    )
    difficulty_html = render_difficulty_badge(difficulty)
    title = issue_data.get("title", "Untitled Issue")
    number = issue_data.get("number", "")
    url = issue_data.get("html_url", "#")

    st.markdown(f"""
<div class="rc-card" style="cursor:pointer;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;">
        <div style="flex:1;min-width:0;">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem;">
                <span style="font-size:0.78rem;color:#6B7890;font-weight:500;">#{number}</span>
                {difficulty_html}
                {labels_html}
            </div>
            <div style="font-weight:600;font-size:0.95rem;color:#17243D;line-height:1.4;margin-bottom:0.35rem;">{title}</div>
            <div style="display:flex;align-items:center;gap:1rem;">{assignee_note}</div>
        </div>
        <div style="text-align:right;flex-shrink:0;">
            <div style="font-size:1.3rem;font-weight:700;color:#159A8C;">{score:.0f}</div>
            <div style="font-size:0.68rem;color:#6B7890;">fit score</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


def render_hint_box(hint_text: str, level: int):
    icon_names = ["lightbulb", "folder", "file_text", "search", "tool"]
    curr_icon = icon(icon_names[min(level - 1, 4)], 15, "#7565C7")
    st.markdown(f"""
<div class="hint-box">
    <div style="font-size:0.75rem;font-weight:600;color:#7565C7;margin-bottom:0.4rem;display:flex;align-items:center;gap:6px;">
        {curr_icon} <span>Hint Level {level}</span>
    </div>
    <div style="color:#17243D;font-size:0.9rem;line-height:1.6;">{hint_text}</div>
</div>
""", unsafe_allow_html=True)


def render_sidebar_nav(current_page: str = ""):
    with st.sidebar:
        # Header styled matching reference Image 2
        compass_svg = icon("compass", 22, "#FFFFFF")
        chevron_down_svg = icon("chevron_down", 14, "#64748B")
        st.markdown(f"""
<div style="margin-bottom:1.25rem;border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:0.9rem;">
    <div style="display:flex;align-items:center;justify-content:space-between;padding:0.2rem 0;">
        <div style="display:flex;align-items:center;gap:0.75rem;">
            <div style="width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,#3B82F6,#1D4ED8);display:grid;place-items:center;box-shadow:0 4px 12px rgba(37,99,235,0.35);">
                {compass_svg}
            </div>
            <div>
                <div style="font-size:0.92rem;font-weight:700;color:#F8FAFC;line-height:1.2;">RepoCompass</div>
                <div style="font-size:0.68rem;color:#94A3B8;font-weight:500;">Pro Plan</div>
            </div>
        </div>
        <span>{chevron_down_svg}</span>
    </div>
</div>
""", unsafe_allow_html=True)

        nav_items = [
            ("Dashboard", "pages/02_dashboard.py", None),
            ("Sakura Trail Arcade", "pages/09_sakura_trail.py", "3D"),
            ("Explore Repos", "pages/03_explore.py", "3"),
            ("My Learning", "pages/04_learning.py", None),
            ("Practice Lab", "pages/05_practice.py", None),
            ("Leaderboard", "pages/06_leaderboard.py", "12"),
            ("Maintainer Studio", "pages/07_maintainer.py", None),
        ]

        for label, page, badge in nav_items:
            badge_str = f"  [{badge}]" if badge else ""
            if st.button(f"{label}{badge_str}", key=f"nav_{label}", use_container_width=True):
                st.switch_page(page)

        st.markdown("""
<div style="margin-top:1.5rem;padding-top:0.8rem;border-top:1px solid rgba(255,255,255,0.08);">
    <div style="font-size:0.68rem;font-weight:700;color:#64748B;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:0.4rem;padding-left:0.4rem;">Account & Profile</div>
</div>
""", unsafe_allow_html=True)

        if st.button("⚙️ Settings & ML Profile", key="nav_settings", use_container_width=True):
            st.switch_page("pages/08_settings.py")

        user = get_current_user()
        if user:
            # Modern bottom profile card with Sign Out below it
            disp_name = user.get("display_name", "Contributor")
            initial = disp_name[0].upper() if disp_name else "C"
            st.markdown(f"""
<div style="margin-top:1.2rem;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:0.75rem;display:flex;align-items:center;gap:10px;">
    <div style="width:36px;height:36px;border-radius:50%;background:linear-gradient(135deg,#3B82F6,#8B5CF6);color:#fff;font-weight:700;display:grid;place-items:center;font-size:0.9rem;flex-shrink:0;">
        {initial}
    </div>
    <div style="flex:1;min-width:0;">
        <div style="font-size:0.84rem;font-weight:600;color:#F8FAFC;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{disp_name}</div>
        <div style="font-size:0.7rem;color:#94A3B8;">Lv. {user.get('level', 1)} · {user.get('xp', 0):,} XP</div>
    </div>
</div>
""", unsafe_allow_html=True)

            if st.button("🚪 Sign Out", key="nav_signout", use_container_width=True, help="Sign out of your account"):
                clear_current_user()
                st.switch_page("streamlit_app.py")
        else:
            if st.button("🔑 Sign In", key="nav_signin", use_container_width=True):
                st.switch_page("streamlit_app.py")

        st.markdown("""
<div style="margin-top:1rem;padding:0.2rem;color:#64748B;font-size:0.72rem;display:flex;align-items:center;gap:6px;">
    <span>RepoCompass v1.2</span> · <span>Zero-Trust Sandbox</span>
</div>
""", unsafe_allow_html=True)


def success_toast(msg: str):
    st.toast(msg)


def error_toast(msg: str):
    st.toast(msg)



def render_tech_orbit():
    """
    Renders the modern animated concentric tech orbit with official SVGs for:
    React, Python, TypeScript, Tailwind CSS, JavaScript, Git, Next.js, HTML5.
    Constructed without newlines or leading spaces so CommonMark never parses
    SVG paths as indented code blocks.
    """
    orbit_nodes = [
        # Orbit 1 (95px): React & Python
        '<div class="orbit-node" style="--r:95px;--angle:45deg;--d:18s;" title="React"><svg width="24" height="24" viewBox="-11.5 -10.23 23 20.46"><circle cx="0" cy="0" r="2" fill="#61DAFB"/><g stroke="#61DAFB" stroke-width="1" fill="none"><ellipse rx="11" ry="4.2"/><ellipse rx="11" ry="4.2" transform="rotate(60)"/><ellipse rx="11" ry="4.2" transform="rotate(120)"/></g></svg></div>',
        '<div class="orbit-node" style="--r:95px;--angle:225deg;--d:18s;" title="Python"><svg width="24" height="24" viewBox="0 0 110 110"><path fill="#3776AB" d="M54.5 5C29.4 5 30.6 15.9 30.6 15.9l.03 11.2h24.4v3.5H20.7S5 28.8 5 54.1s13.8 24.5 13.8 24.5h8.2v-11.6s-.4-13.8 13.6-13.8h23.5s13.2.2 13.2-12.8V17.8S80.9 5 54.5 5zm-13.8 7.4a3.8 3.8 0 1 1 0 7.6 3.8 3.8 0 0 1 0-7.6z"/><path fill="#FFD43B" d="M55.5 105c25.1 0 23.9-10.9 23.9-10.9l-.03-11.2H55v-3.5h34.3s15.7 1.8 15.7-23.5-13.8-24.5-13.8-24.5h-8.2v11.6s.4 13.8-13.6 13.8H45.9s-13.2-.2-13.2 12.8v12.6S29.1 105 55.5 105zm13.8-7.4a3.8 3.8 0 1 1 0-7.6 3.8 3.8 0 0 1 0 7.6z"/></svg></div>',
        
        # Orbit 2 (150px): TypeScript & Tailwind CSS
        '<div class="orbit-node" style="--r:150px;--angle:120deg;--d:26s;--dir:reverse;" title="TypeScript"><svg width="26" height="26" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#3178C6"/><text x="16" y="21.5" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-weight="900" font-size="14" fill="#FFFFFF" text-anchor="middle">TS</text></svg></div>',
        '<div class="orbit-node" style="--r:150px;--angle:300deg;--d:26s;--dir:reverse;" title="Tailwind CSS"><svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12.001 4.8c-3.2 0-5.2 1.6-6 4.8 1.2-1.6 2.6-2.2 4.2-1.8.9.2 1.5.9 2.3 1.6C13.7 10.6 15 12 18 12c3.2 0 5.2-1.6 6-4.8-1.2 1.6-2.6 2.2-4.2 1.8-.9-.2-1.5-.9-2.3-1.6C16.3 6.2 15 4.8 12 4.8zm-6 7.2c-3.2 0-5.2 1.6-6 4.8 1.2-1.6 2.6-2.2 4.2-1.8.9.2 1.5.9 2.3 1.6 1.2 1.2 2.5 2.6 5.5 2.6 3.2 0 5.2-1.6 6-4.8-1.2 1.6-2.6 2.2-4.2 1.8-.9-.2-1.5-.9-2.3-1.6-1.2-1.2-2.5-2.6-5.5-2.6z" fill="#06B6D4"/></svg></div>',
        
        # Orbit 3 (210px): JavaScript & Git
        '<div class="orbit-node" style="--r:210px;--angle:10deg;--d:34s;" title="JavaScript"><svg width="26" height="26" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#F7DF1E"/><text x="16" y="21.5" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-weight="900" font-size="14" fill="#000000" text-anchor="middle">JS</text></svg></div>',
        '<div class="orbit-node" style="--r:210px;--angle:190deg;--d:34s;" title="Git"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#F05032" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M6 9v12"/><path d="M18 9a9 9 0 0 0-9 9"/></svg></div>',
        
        # Orbit 4 (265px): Next.js & HTML5 / Code
        '<div class="orbit-node" style="--r:265px;--angle:70deg;--d:42s;--dir:reverse;" title="Next.js"><svg width="24" height="24" viewBox="0 0 180 180"><circle cx="90" cy="90" r="90" fill="#000000"/><path fill="#FFFFFF" d="M149.5 159.5L69.7 57H54v66h11.8V72.2l71.7 92.4c4.3-1.6 8.3-3.3 12-5.1zM115.5 57h11.8v44.2H115.5z"/></svg></div>',
        '<div class="orbit-node" style="--r:265px;--angle:250deg;--d:42s;--dir:reverse;" title="HTML5 / Code"><svg width="26" height="26" viewBox="0 0 32 32"><rect width="32" height="32" rx="6" fill="#E34F26"/><text x="16" y="21.5" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" font-weight="900" font-size="13" fill="#FFFFFF" text-anchor="middle">&lt;/&gt;</text></svg></div>',
    ]
    html = (
        '<div class="orbit-stage">'
        '<div class="orbit-center-title">RepoCompass</div>'
        '<div class="ripple-ring" style="width:180px;height:180px;animation-delay:0s;"></div>'
        '<div class="ripple-ring" style="width:300px;height:300px;animation-delay:0.6s;"></div>'
        '<div class="ripple-ring" style="width:420px;height:420px;animation-delay:1.2s;"></div>'
        '<div class="ripple-ring" style="width:530px;height:530px;animation-delay:1.8s;"></div>'
        '<svg class="orbit-svg" viewBox="0 0 600 600">'
        '<circle cx="300" cy="300" r="95" fill="none" stroke="#E5E7EB" stroke-width="1.2" stroke-dasharray="4 4" />'
        '<circle cx="300" cy="300" r="150" fill="none" stroke="#E5E7EB" stroke-width="1.2" stroke-dasharray="5 5" />'
        '<circle cx="300" cy="300" r="210" fill="none" stroke="#E5E7EB" stroke-width="1.2" stroke-dasharray="6 6" />'
        '<circle cx="300" cy="300" r="265" fill="none" stroke="#E5E7EB" stroke-width="1.2" stroke-dasharray="6 6" />'
        '</svg>'
        + "".join(orbit_nodes)
        + '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


from app.ui.workflow_chart import render_workflow_infographic, generate_mermaid_workflow
