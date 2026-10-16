"""
Shared Streamlit UI utilities: theme, session state helpers, components.
"""
from __future__ import annotations

import streamlit as st
from typing import Optional
from app.ui.icons import icon


# ─── Solo Ledger Design Tokens (§2.1, §2.2, §2.9) ───────────────────────────

COLORS = {
    # Canvas & structure
    "canvas": "#F6EFE3",
    "surface": "#FBF6EC",
    "ink": "#111111",
    "text_muted": "#4F5C57",
    "rule": "#D9CFBB",
    "topbar": "#214F4B",
    "topbar_text": "#E8F1EC",
    "topbar_dim": "#A9C7BE",
    # Pastel fills
    "mint": "#DCEBE0",
    "tan": "#F1E3C6",
    "slate_blue": "#DCE5E5",
    "salmon": "#E8C4B8",
    "ai_lilac": "#ECE8FA",
    "ai_text": "#4A3F8F",
    # Semantic
    "green": "#2E6B4A",
    "teal": "#159A8C",
    "amber": "#8A5E10",
    "amber_chart": "#B98A2E",
    "error": "#C94C4C",
    "amber_strong": "#6F4A00",
    "link": "#0B6E64",
    "error_text": "#9E3333",
    "error_soft": "#F6D9D9",
    "on_ink": "#F6EFE3",
    "focus_on_fill": "#111111",
    "scrim": "rgba(17,17,17,0.55)",
    "dash": "#4F5C57",
    # Deep surface palette
    "navy": "#101B35",
    "navy_surface": "#172544",
    "mint_light": "#DDF7F3",
    "ai_accent": "#7565C7",
    "text_main": "#17243D",
}


# ─── Global CSS (§2.9 & Component Styling) ─────────────────────────────────

def inject_global_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;800&display=swap');

:root {
  /* canvas & structure */
  --canvas: #F6EFE3;
  --surface: #FBF6EC;
  --ink: #111111;
  --text-muted: #4F5C57;
  --rule: #D9CFBB;
  --topbar: #214F4B;
  --topbar-text: #E8F1EC;
  --topbar-dim: #A9C7BE;
  /* pastel fills */
  --mint: #DCEBE0;
  --tan: #F1E3C6;
  --slate-blue: #DCE5E5;
  --salmon: #E8C4B8;
  --ai-lilac: #ECE8FA;
  --ai-text: #4A3F8F;
  /* semantic */
  --green: #2E6B4A;
  --teal: #159A8C;
  --amber: #8A5E10;
  --amber-chart: #B98A2E;
  --error: #C94C4C;
  /* original PRD deep-surface palette */
  --navy: #101B35;
  --navy-surface: #172544;
  --mint-light: #DDF7F3;
  --ai-accent: #7565C7;
  --text-main: #17243D;
  /* token additions (§2.2) */
  --amber-strong: #6F4A00;
  --link: #0B6E64;
  --error-text: #9E3333;
  --error-soft: #F6D9D9;
  --on-ink: #F6EFE3;
  --focus-on-fill: #111111;
  --scrim: rgba(17,17,17,0.55);
  --dash: #4F5C57;
  /* type */
  --font-sans: "Space Grotesk", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  /* spacing */
  --s-1: 4px; --s-2: 8px; --s-3: 12px; --s-4: 16px; --s-5: 20px; --s-6: 24px; --s-8: 32px; --s-10: 40px; --s-12: 48px; --s-16: 64px;
  /* shape */
  --radius-card: 14px;
  --radius-control: 12px;
  --radius-inner: 8px;
  --radius-pill: 999px;
  --bw-card: 2px solid var(--ink);
  --bw-pill: 1.5px solid currentColor;
  --bw-rule: 1px solid var(--rule);
  --bw-rule-head: 2px solid var(--ink);
  --bw-dash: 1.5px dashed var(--dash);
  /* layout */
  --content-max: 1440px;
  --sidebar-w: 248px;
  --rail-w: 72px;
  --gap: 16px;
  --control-h: 44px;
  /* motion */
  --dur-fast: 150ms;
  --dur-base: 200ms;
  --dur-slow: 250ms;
  --ease: cubic-bezier(0.2, 0, 0, 1);
  /* focus */
  --focus-ring: 2px solid var(--teal);
  --focus-offset: 2px;
}

:root { color-scheme: light; }

/* ── Reset & Base (§1 P8: Flat colour, 2px ink outlines, no shadows, no gradients) ── */
html, body, [class*="css"], [data-testid="stAppViewContainer"], .stApp {
    background: var(--canvas) !important;
    color: var(--ink) !important;
    font-family: var(--font-sans) !important;
    font-size: 16px;
    line-height: 1.5;
}

.main .block-container {
    padding-top: 1rem;
    padding-bottom: 3rem;
    max-width: var(--content-max);
}

/* ── Typography Classes (§2.4) ────────────────────────────────────────── */
.t-kpi-xl { font-family: var(--font-mono) !important; font-size: 84px !important; line-height: 1 !important; font-weight: 800 !important; letter-spacing: -0.03em !important; font-variant-numeric: tabular-nums; }
.t-kpi-lg { font-family: var(--font-mono) !important; font-size: 56px !important; line-height: 1 !important; font-weight: 800 !important; letter-spacing: -0.03em !important; font-variant-numeric: tabular-nums; }
.t-kpi-md { font-family: var(--font-mono) !important; font-size: 40px !important; line-height: 44px !important; font-weight: 800 !important; letter-spacing: -0.03em !important; font-variant-numeric: tabular-nums; }
.t-display { font-family: var(--font-sans) !important; font-size: 56px !important; line-height: 60px !important; font-weight: 700 !important; letter-spacing: -0.02em !important; }
.t-page-title { font-family: var(--font-sans) !important; font-size: 34px !important; line-height: 40px !important; font-weight: 700 !important; letter-spacing: -0.01em !important; }
.t-h2 { font-family: var(--font-sans) !important; font-size: 26px !important; line-height: 32px !important; font-weight: 700 !important; }
.t-h3 { font-family: var(--font-sans) !important; font-size: 20px !important; line-height: 26px !important; font-weight: 600 !important; }
.t-h4 { font-family: var(--font-sans) !important; font-size: 17px !important; line-height: 23px !important; font-weight: 600 !important; }
.t-body-lg { font-family: var(--font-sans) !important; font-size: 18px !important; line-height: 28px !important; }
.t-body { font-family: var(--font-sans) !important; font-size: 15px !important; line-height: 22px !important; }
.t-body-sm { font-family: var(--font-sans) !important; font-size: 13px !important; line-height: 19px !important; }
.t-eyebrow { font-family: var(--font-mono) !important; font-size: 11px !important; line-height: 16px !important; font-weight: 600 !important; letter-spacing: 0.1em !important; text-transform: uppercase !important; }
.t-label { font-family: var(--font-mono) !important; font-size: 12px !important; line-height: 16px !important; font-weight: 500 !important; }
.t-pill { font-family: var(--font-mono) !important; font-size: 10px !important; line-height: 12px !important; font-weight: 600 !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; }
.t-button { font-family: var(--font-mono) !important; font-size: 11px !important; line-height: 16px !important; font-weight: 600 !important; letter-spacing: 0.08em !important; text-transform: uppercase !important; }
.t-code { font-family: var(--font-mono) !important; font-size: 13px !important; line-height: 20px !important; }

/* ── Sidebar Solo Ledger (§3.2) ────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 2px solid var(--ink) !important;
}

[data-testid="stSidebar"] * {
    color: var(--ink) !important;
    font-family: var(--font-sans) !important;
}

/* Hide Streamlit's default auto-generated page navigation (causes duplicates) */
[data-testid="stSidebar"] [data-testid="stSidebarNav"],
[data-testid="stSidebar"] nav[data-testid="stSidebarNav"],
[data-testid="stSidebarNav"] {
    display: none !important;
    height: 0 !important;
    overflow: hidden !important;
}

/* Sidebar collapse/expand toggle button — replace text with chevron symbol */
[data-testid="collapsedControl"] {
    background: var(--surface) !important;
    border: 2px solid var(--ink) !important;
    border-radius: 8px !important;
    box-shadow: none !important;
}
[data-testid="collapsedControl"] button {
    color: var(--ink) !important;
}

[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: var(--ink) !important;
    border: 2px solid transparent !important;
    border-radius: var(--radius-control) !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    padding: 0.55rem 0.9rem !important;
    width: 100%;
    text-align: left;
    transition: all var(--dur-fast) ease;
    display: flex;
    align-items: center;
    gap: 8px;
    box-shadow: none !important;
}

[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--canvas) !important;
    border-color: var(--rule) !important;
}

/* ── Official Social Login Button Styling ──────────────────────────────── */
.social-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    width: 100%;
    height: 48px;
    border-radius: 10px;
    font-family: var(--font-sans);
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    text-decoration: none;
    box-sizing: border-box;
}
.social-btn svg {
    flex-shrink: 0;
}
.social-btn-github {
    background: #24292f;
    border: 2px solid #24292f;
    color: #ffffff;
}
.social-btn-github:hover {
    background: #3b3f46;
}
.social-btn-google {
    background: #ffffff;
    border: 2px solid var(--ink);
    color: var(--ink);
}
.social-btn-google:hover {
    background: #f8f9fa;
}

/* ── Buttons (§3.4) ───────────────────────────────────────────────────── */
.stButton > button[kind="primary"] {
    background: var(--ink) !important;
    color: var(--on-ink) !important;
    border: 2px solid var(--ink) !important;
    border-radius: var(--radius-control) !important;
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    padding: 0.65rem 1.25rem !important;
    transition: all var(--dur-fast) ease !important;
    box-shadow: none !important;
}

.stButton > button[kind="primary"]:hover {
    background: var(--topbar) !important;
    border-color: var(--ink) !important;
    transform: translateY(-1px) !important;
}

.stButton > button[kind="primary"]:active {
    transform: translateY(1px) !important;
}

.stButton > button[kind="secondary"], .stButton > button:not([kind="primary"]) {
    background: var(--surface) !important;
    color: var(--ink) !important;
    border: 2px solid var(--ink) !important;
    border-radius: var(--radius-control) !important;
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    padding: 0.65rem 1.25rem !important;
    transition: all var(--dur-fast) ease !important;
    box-shadow: none !important;
}

.stButton > button[kind="secondary"]:hover, .stButton > button:not([kind="primary"]):hover {
    background: var(--mint) !important;
    border-color: var(--ink) !important;
}

/* ── Cards (§3.6) ─────────────────────────────────────────────────────── */
.rc-card {
    background: var(--surface);
    border: var(--bw-card);
    border-radius: var(--radius-card);
    padding: var(--s-5);
    margin-bottom: var(--s-4);
    box-shadow: none !important;
}

.card--mint { background: var(--mint) !important; }
.card--tan { background: var(--tan) !important; }
.card--slate { background: var(--slate-blue) !important; }
.card--salmon { background: var(--salmon) !important; color: var(--ink) !important; }
.card--ai { background: var(--ai-lilac) !important; border: 2px solid var(--ai-text) !important; color: var(--ai-text) !important; }
.card--navy { background: var(--navy) !important; color: var(--mint-light) !important; border: 2px solid var(--ink) !important; }

/* ── Pills & Tags (§3.5) ──────────────────────────────────────────────── */
.pill {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    height: 24px;
    padding: 0 10px;
    border-radius: var(--radius-pill);
    border: var(--bw-pill);
    font-family: var(--font-mono);
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.pill-green { color: var(--green); border-color: var(--green); background: transparent; }
.pill-amber { color: var(--amber-strong); border-color: var(--amber-strong); background: transparent; }
.pill-assigned { color: var(--ink); border-color: var(--ink); background: var(--tan); }
.pill-ai { color: var(--ai-text); border-color: var(--ai-text); background: var(--ai-lilac); }
.pill-sample { color: var(--ink); border: 1.5px dashed var(--ink); background: var(--tan); }
.pill-neutral { color: var(--text-muted); border-color: var(--text-muted); background: transparent; }

/* ── Progress / XP Bar (§3.6.6) ───────────────────────────────────────── */
.ledger-progress-track {
    background: var(--surface);
    border: 2px solid var(--ink);
    border-radius: 999px;
    height: 16px;
    overflow: hidden;
    position: relative;
    margin: 6px 0;
}

.ledger-progress-fill {
    height: 100%;
    background: var(--green);
    border-right: 2px solid var(--ink);
    transition: width var(--dur-slow) var(--ease);
}

/* ── Inputs, Textareas, Selectboxes ───────────────────────────────────── */
.stTextInput > div > div > input, .stTextArea textarea, [data-baseweb="select"] {
    background: var(--surface) !important;
    border: 2px solid var(--ink) !important;
    border-radius: var(--radius-control) !important;
    font-family: var(--font-sans) !important;
    color: var(--ink) !important;
    box-shadow: none !important;
}

.stTextInput > div > div > input:focus, .stTextArea textarea:focus {
    outline: var(--focus-ring) !important;
    outline-offset: var(--focus-offset) !important;
}

/* ── Tabs (§3.11) ─────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    border-bottom: 2px solid var(--ink) !important;
    gap: 12px;
}

.stTabs [data-baseweb="tab"] {
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    border-bottom: 4px solid transparent !important;
    background: transparent !important;
    padding: 10px 16px !important;
}

.stTabs [data-baseweb="tab"]:hover {
    background: var(--mint) !important;
    color: var(--ink) !important;
}

.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: var(--ink) !important;
    border-bottom: 4px solid var(--teal) !important;
}

/* ── Metrics Override ─────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: var(--surface) !important;
    border: 2px solid var(--ink) !important;
    border-radius: var(--radius-card) !important;
    padding: 16px !important;
    box-shadow: none !important;
}

[data-testid="stMetric"] * {
    color: var(--ink) !important;
    font-family: var(--font-sans) !important;
}

[data-testid="stMetricValue"] {
    font-family: var(--font-mono) !important;
    font-weight: 800 !important;
}

/* ── Code & Mono ──────────────────────────────────────────────────────── */
code, pre, .mono {
    font-family: var(--font-mono) !important;
}

/* ── Focus rings ──────────────────────────────────────────────────────── */
:focus-visible {
    outline: var(--focus-ring);
    outline-offset: var(--focus-offset);
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


# ─── HTML Safety Clean Helper ──────────────────────────────────────────────

def clean_html(html_str: str) -> str:
    """
    Strips leading whitespace from every line of an HTML string so that
    Streamlit's Markdown parser never interprets indented HTML lines as code blocks.
    """
    if not html_str:
        return ""
    return "\n".join(line.strip() for line in html_str.splitlines() if line.strip())


# ─── Top Status Bar (§3.1) ─────────────────────────────────────────────────

def render_top_status_bar(is_live: bool = True, sync_time: Optional[str] = None):
    """
    Renders truthful, ambient system status bar (§3.1):
    ● LIVE · SYNCED 14:32 │ GITHUB ✓  DB ✓  OLLAMA ✓ qwen3:4b │ OCT 2026 · LVL 03
    """
    from datetime import datetime
    from app.services.llm_service import check_ollama_available
    from app.core.config import get_settings

    settings = get_settings()
    now_str = sync_time or datetime.now().strftime("%H:%M")
    user = get_current_user()
    lvl = user.get("level", 1) if user else 1

    ollama_ok = check_ollama_available()
    model_name = settings.ollama_model.split(":")[0] if settings.ollama_model else "qwen3"
    ollama_str = f"OLLAMA ✓ {model_name}" if ollama_ok else "OLLAMA ⚠ unavailable"
    sync_str = f"● LIVE · SYNCED {now_str}" if is_live else f"◐ CACHED · {now_str}"

    topbar_html = (
        '<div style="background:var(--topbar);color:var(--topbar-text);border-bottom:2px solid var(--ink);padding:7px 1.5rem;font-family:var(--font-mono);font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;display:flex;align-items:center;justify-content:space-between;margin:-1rem -1rem 1.25rem -1rem;position:sticky;top:0;z-index:50;">'
        + f'<div style="display:flex;align-items:center;gap:8px;"><span style="color:var(--mint);">{sync_str}</span></div>'
        + f'<div style="display:flex;align-items:center;gap:20px;color:var(--topbar-dim);"><span>GITHUB ✓</span><span>DB ✓</span><span>{ollama_str}</span></div>'
        + f'<div style="color:var(--topbar-text);"><span>OCT 2026 · LVL {lvl:02d}</span></div>'
        + '</div>'
    )
    st.markdown(topbar_html, unsafe_allow_html=True)


# ─── Page Title Pattern (§2.4) ─────────────────────────────────────────────

def render_page_header(primary: str, secondary: str, caption: str = ""):
    """
    Page title pattern (§2.4):
    <strong>Contribution Health</strong> <span class="t-secondary">/ At a Glance</span>
    """
    cap_html = f"<p style='color:var(--text-muted);font-family:var(--font-sans);font-size:14px;margin:0.25rem 0 1.25rem 0;'>{caption}</p>" if caption else "<div style='height:0.75rem;'></div>"
    header_html = (
        '<div style="margin-bottom:0.75rem;">'
        + f'<h1 style="font-family:var(--font-sans);font-size:32px;font-weight:700;color:var(--ink);margin:0;line-height:1.2;letter-spacing:-0.01em;">{primary} <span style="font-weight:400;color:var(--text-muted);">/ {secondary}</span></h1>'
        + f'{cap_html}'
        + '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


# ─── KPI & Metrics Cards (§3.6.1, §3.6.3) ──────────────────────────────────

def render_kpi_card(
    title: str,
    value: str,
    subtext: str = "",
    delta: Optional[str] = None,
    fill: str = "surface",
    status: str = "ON TRACK",
    sparkline: Optional[list] = None
):
    """Renders a Solo Ledger KPI card with flat heavy 2px outline and optional pastel fill."""
    fill_cls = f"card--{fill}" if fill != "surface" else ""
    pill_html = f'<span class="pill pill-green">● {status}</span>' if status else ""
    delta_html = f'<div style="font-family:var(--font-sans);font-size:13px;color:var(--green);font-weight:600;margin-top:4px;">▲ {delta}</div>' if delta else ""
    sub_html = f'<div style="font-family:var(--font-mono);font-size:12px;color:var(--text-muted);margin-top:6px;">{subtext}</div>' if subtext else ""

    spark_html = ""
    if sparkline and len(sparkline) >= 4:
        max_val = max(sparkline) or 1
        pts = " ".join(f"{i * 20},{30 - int((v / max_val) * 24)}" for i, v in enumerate(sparkline[:7]))
        spark_html = (
            '<div style="margin-top:10px;">'
            + f'<svg width="140" height="32" viewBox="0 0 140 32" style="overflow:visible;">'
            + f'<polyline points="{pts}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
            + '</svg></div>'
        )

    card_content = (
        f'<div class="rc-card {fill_cls}">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">'
        + f'<span class="t-eyebrow" style="color:var(--ink);">{title}</span>'
        + f'{pill_html}'
        + '</div>'
        + f'<div class="t-kpi-lg" style="color:var(--ink);margin:0.2rem 0;">{value}</div>'
        + f'{delta_html}'
        + f'{sub_html}'
        + f'{spark_html}'
        + '</div>'
    )
    st.markdown(card_content, unsafe_allow_html=True)


def render_mini_stat_card(label: str, number: str, caption: str):
    """Renders mini stat card (§3.6.3) with dashed divider."""
    card_html = (
        '<div class="rc-card" style="padding:16px;">'
        + f'<div class="t-eyebrow" style="color:var(--text-muted);margin-bottom:4px;">{label}</div>'
        + f'<div class="t-kpi-md" style="color:var(--ink);margin:2px 0;">{number}</div>'
        + '<div style="border-top:var(--bw-dash);margin:10px 0 8px 0;"></div>'
        + f'<div class="t-label" style="color:var(--text-muted);">{caption}</div>'
        + '</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)


# ─── Status Pills (§3.5) ───────────────────────────────────────────────────

def render_status_pill(status_type: str, label: Optional[str] = None) -> str:
    """Returns exact status pill HTML per §3.5."""
    st_clean = status_type.lower().replace(" ", "_")
    if st_clean in ("on_track", "success", "completed"):
        return f'<span class="pill pill-green">● {label or "ON TRACK"}</span>'
    elif st_clean in ("needs_info", "warning", "needs_more_info"):
        return f'<span class="pill pill-amber">⚠ {label or "NEEDS MORE INFO"}</span>'
    elif st_clean in ("assigned", "in_progress"):
        return f'<span class="pill pill-assigned">● {label or "ASSIGNED"}</span>'
    elif st_clean in ("ai", "ai_generated"):
        return f'<span class="pill pill-ai">✦ {label or "AI-GENERATED"}</span>'
    elif st_clean == "sample":
        return f'<span class="pill pill-sample">◇ {label or "SAMPLE DATA"}</span>'
    elif st_clean in ("beginner", "est._beginner"):
        return f'<span class="pill pill-green">▲ {label or "EST. BEGINNER"}</span>'
    elif st_clean in ("intermediate", "est._intermediate"):
        return f'<span class="pill pill-amber">▲▲ {label or "EST. INTERMEDIATE"}</span>'
    elif st_clean in ("advanced", "est._advanced"):
        return f'<span class="pill" style="color:var(--ink);border-color:var(--ink);background:transparent;">▲▲▲ {label or "EST. ADVANCED"}</span>'
    elif st_clean in ("live", "live_sync"):
        return f'<span class="pill pill-green">● {label or "LIVE"}</span>'
    elif st_clean in ("cached", "provisional"):
        return f'<span class="pill pill-neutral">◐ {label or "CACHED"}</span>'
    else:
        return f'<span class="pill pill-neutral">○ {label or status_type.upper()}</span>'


# ─── AI-Generated Block (§3.11) ───────────────────────────────────────────

def render_ai_block(content: str, model: str = "qwen3:4b", timestamp: str = "14:32", sources: Optional[list] = None):
    """Renders lilac AI-generated block with mandatory disclaimer and evidence footer (§3.11)."""
    src_html = ""
    if sources:
        src_items = " · ".join(f"<code>{s}</code>" for s in sources)
        src_html = f"<div style='margin-top:8px;font-family:var(--font-mono);font-size:11px;color:var(--ai-text);'>SOURCES: {src_items}</div>"

    ai_html = (
        '<div class="rc-card card--ai" style="padding:16px;margin:12px 0;">'
        + '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">'
        + f'<span class="t-pill" style="color:var(--ai-text);">✦ AI-GENERATED · {model} · {timestamp}</span>'
        + '<span class="t-label" style="color:var(--ai-text);font-size:11px;">May be wrong. Check the sources.</span>'
        + '</div>'
        + f'<div style="font-family:var(--font-sans);font-size:14px;line-height:1.6;color:var(--ink);">{content}</div>'
        + f'{src_html}'
        + '</div>'
    )
    st.markdown(ai_html, unsafe_allow_html=True)


# ─── Evidence & Empty States (§3.7) ────────────────────────────────────────

def render_empty_repository_spec(files_searched: Optional[list] = None):
    """Verbatim required empty state (§3.7)."""
    files = ", ".join(files_searched or ["README.md", "CONTRIBUTING.md", "package.json"])
    empty_html = (
        '<div style="background:var(--surface);border:2px dashed var(--ink);border-radius:14px;padding:20px;margin:1rem 0;">'
        + '<div style="font-family:var(--font-sans);font-weight:600;font-size:16px;color:var(--ink);display:flex;align-items:center;gap:8px;">'
        + '<span style="font-family:var(--font-mono);font-size:18px;">○</span> Not specified in the repository.'
        + '</div>'
        + f'<div style="font-family:var(--font-mono);font-size:12px;color:var(--text-muted);margin-top:6px;">We looked in: <code>{files}</code></div>'
        + '</div>'
    )
    st.markdown(empty_html, unsafe_allow_html=True)


def render_evidence_badge(badge_type: str) -> str:
    """Evidence badge pill (§3.7): VERIFIED, INFERRED, NOT FOUND."""
    b_clean = badge_type.lower()
    if b_clean in ("verified", "direct"):
        return '<span class="pill pill-green">✓ VERIFIED</span>'
    elif b_clean in ("inferred", "related"):
        return '<span class="pill pill-amber">◐ INFERRED</span>'
    elif b_clean in ("not_found", "none"):
        return '<span class="pill" style="color:var(--text-muted);border:1.5px dashed var(--text-muted);background:transparent;">○ NOT FOUND</span>'
    elif b_clean in ("ai", "ai_inferred"):
        return '<span class="pill pill-ai">✦ AI-INFERRED</span>'
    return f'<span class="pill pill-neutral">○ {badge_type.upper()}</span>'


# ─── Level Badge & XP Progress (§3.6.6) ────────────────────────────────────

def render_level_badge(level: int, xp: int, xp_into: int, xp_needed: int):
    """Solo Ledger XP Progress Card with exact tokens."""
    pct = min(int(xp_into / max(xp_needed, 1) * 100), 100)
    badge_html = (
        '<div class="rc-card card--mint" style="padding:16px;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
        + f'<span class="t-eyebrow" style="color:var(--ink);">LVL {level:02d}</span>'
        + f'<span class="t-label" style="color:var(--text-muted);">{xp_into:,} / {xp_needed:,} XP</span>'
        + '</div>'
        + '<div class="ledger-progress-track">'
        + f'<div class="ledger-progress-fill" style="width:{pct}%;"></div>'
        + '</div>'
        + '<div style="display:flex;justify-content:space-between;font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-top:4px;">'
        + f'<span>{xp_needed - xp_into} XP to Level {level + 1}</span>'
        + f'<span>{xp:,} XP total</span>'
        + '</div></div>'
    )
    st.markdown(badge_html, unsafe_allow_html=True)


def render_difficulty_badge(difficulty: str) -> str:
    return render_status_pill(difficulty)


# ─── Issue Card (§3.8) ─────────────────────────────────────────────────────

def render_issue_card(issue_data: dict, score: float, difficulty: str, fit_reason: Optional[str] = None):
    """
    Renders Solo Ledger Issue Card (§3.8) with mono numbers, tags,
    AI fit block, readiness score, and real action buttons.
    """
    number = issue_data.get("number", "101")
    title = issue_data.get("title", "Untitled Issue")
    labels = issue_data.get("labels") or []
    assignees = issue_data.get("assignees") or []
    diff_pill = render_status_pill(difficulty)

    tags_html = " ".join(
        f'<span class="pill pill-neutral" style="height:20px;padding:0 8px;font-size:9px;">{l}</span>'
        for l in labels[:4]
    )

    assignee_html = (
        f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--ink);background:var(--tan);padding:2px 6px;border-radius:4px;border:1px solid var(--ink);">● ASSIGNED · @{assignees[0]}</span>'
        if assignees
        else '<span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">○ No assignee listed</span>'
    )

    fit_block_html = ""
    if fit_reason:
        fit_block_html = (
            '<div style="background:var(--ai-lilac);border:1.5px solid var(--ai-text);border-radius:8px;padding:10px 14px;margin:10px 0;">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
            + '<span class="t-pill" style="color:var(--ai-text);">✦ WHY THIS FITS</span>'
            + f'<span class="t-label" style="color:var(--ai-text);">Readiness {score:.0f}/100 (est.)</span>'
            + '</div>'
            + f'<div style="font-family:var(--font-sans);font-size:13px;color:var(--ink);line-height:1.4;">{fit_reason}</div>'
            + '</div>'
        )

    issue_html = (
        '<div class="rc-card" style="margin-bottom:14px;">'
        + '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;">'
        + '<div style="flex:1;min-width:0;">'
        + '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
        + f'<span class="t-label" style="font-weight:700;color:var(--ink);">#{number}</span>'
        + f'{diff_pill}'
        + f'{tags_html}'
        + '</div>'
        + f'<div class="t-h4" style="color:var(--ink);margin-bottom:6px;line-height:1.3;">{title}</div>'
        + '<div style="display:flex;align-items:center;gap:12px;margin-bottom:4px;">'
        + f'{assignee_html}'
        + '<span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">· Updated recently</span>'
        + '</div>'
        + f'{fit_block_html}'
        + '</div>'
        + '<div style="text-align:right;flex-shrink:0;">'
        + f'<div class="t-kpi-md" style="color:var(--green);">{score:.0f}</div>'
        + '<div class="t-eyebrow" style="color:var(--text-muted);">FIT SCORE</div>'
        + '</div></div></div>'
    )
    st.markdown(issue_html, unsafe_allow_html=True)


# ─── Hint Ladder Box (§3.9.1) ──────────────────────────────────────────────

def render_hint_box(hint_text: str, level: int):
    """Solo Ledger Hint Ladder Step (§3.9.1)."""
    hint_html = (
        '<div class="rc-card card--salmon" style="padding:16px;margin:10px 0;">'
        + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
        + '<div style="display:flex;align-items:center;gap:8px;">'
        + f'<div style="width:26px;height:26px;border-radius:50%;background:var(--ink);color:var(--on-ink);display:grid;place-items:center;font-family:var(--font-mono);font-size:12px;font-weight:800;">{level}</div>'
        + f'<span class="t-eyebrow" style="color:var(--ink);">HINT LEVEL {level} · REVEALED</span>'
        + '</div>'
        + '<span class="t-pill" style="color:var(--ink);border-color:var(--ink);">✓ GUIDANCE</span>'
        + '</div>'
        + f'<div style="background:var(--surface);border:2px solid var(--ink);border-radius:8px;padding:12px 16px;font-family:var(--font-sans);font-size:14px;color:var(--ink);line-height:1.5;">{hint_text}</div>'
        + '<div style="font-family:var(--font-mono);font-size:11px;color:var(--ink);margin-top:8px;">Hints are guidance, not a verified fix. Check with repository tests.</div>'
        + '</div>'
    )
    st.markdown(hint_html, unsafe_allow_html=True)


# ─── Code-Trail Chain (§3.9.2) ─────────────────────────────────────────────

def render_code_trail_chain(nodes: List[Dict[str, Any]]):
    """
    Renders Solo Ledger Code-Trail Chain (§3.9.2):
    Nodes: Issue → File → Symbol → Test
    Each node has type eyebrow, mono identifier, match pill, and reason.
    Constructed safely without multiline indentations.
    """
    node_cards = []
    for i, n in enumerate(nodes):
        ntype = n.get("type", "NODE").upper()
        name = n.get("name", "—")
        match_type = n.get("match", "direct")
        reason = n.get("reason", "")
        url = n.get("url")

        if match_type == "direct":
            pill = '<span class="pill pill-green" style="font-size:9px;">✓ DIRECT MATCH</span>'
        elif match_type == "related":
            pill = '<span class="pill pill-amber" style="font-size:9px;">◐ RELATED REFERENCE</span>'
        elif match_type == "ai":
            pill = '<span class="pill pill-ai" style="font-size:9px;">✦ AI-INFERRED</span>'
        else:
            pill = '<span class="pill" style="color:var(--text-muted);border:1px dashed var(--text-muted);font-size:9px;">○ NOT FOUND</span>'

        link_html = f'<a href="{url}" target="_blank" rel="noopener noreferrer" style="font-family:var(--font-mono);font-size:11px;color:var(--link);text-decoration:underline;margin-top:6px;display:inline-block;">↗ GitHub</a>' if url else ""

        card_html = (
            '<div style="flex:1;min-width:180px;background:var(--surface);border:2px solid var(--ink);border-radius:10px;padding:12px 14px;">'
            + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
            + f'<span class="t-eyebrow" style="color:var(--text-muted);">{ntype}</span>'
            + f'{pill}'
            + '</div>'
            + f'<div style="font-family:var(--font-mono);font-size:13px;font-weight:700;color:var(--ink);word-break:break-all;margin:4px 0;">{name}</div>'
            + f'<div style="font-family:var(--font-sans);font-size:12px;color:var(--ink);line-height:1.4;">{reason}</div>'
            + f'{link_html}'
            + '</div>'
        )
        node_cards.append(card_html)

    chain_items = []
    for idx, c in enumerate(node_cards):
        chain_items.append(c)
        if idx < len(node_cards) - 1:
            arrow = '<div style="display:flex;align-items:center;justify-content:center;padding:0 6px;"><span style="font-family:var(--font-mono);font-size:20px;font-weight:900;color:var(--ink);">→</span></div>'
            chain_items.append(arrow)

    st.markdown(
        '<div style="display:flex;align-items:stretch;gap:8px;flex-wrap:wrap;margin:1rem 0;">'
        + ''.join(chain_items)
        + '</div>',
        unsafe_allow_html=True
    )


# ─── Diff Viewer (§3.10) ───────────────────────────────────────────────────

def render_diff_viewer(diff_text: str, filename: str = "patch.diff"):
    """
    Renders Solo Ledger light readable Diff Viewer (§3.10):
    Container --surface, 2px ink border, radius 8px, t-code.
    Added lines --mint bg with +, removed lines --salmon bg with -.
    """
    if not diff_text or not diff_text.strip():
        empty_diff = (
            '<div style="background:var(--surface);border:2px dashed var(--ink);border-radius:8px;padding:24px;text-align:center;">'
            + '<div style="font-family:var(--font-mono);font-size:13px;color:var(--text-muted);">Paste a unified diff or write a plan to review.</div>'
            + '</div>'
        )
        st.markdown(empty_diff, unsafe_allow_html=True)
        return

    lines = diff_text.splitlines()
    additions = sum(1 for l in lines if l.startswith("+") and not l.startswith("+++"))
    deletions = sum(1 for l in lines if l.startswith("-") and not l.startswith("---"))

    formatted_lines = []
    for l in lines:
        escaped = html.escape(l)
        if l.startswith("+") and not l.startswith("+++"):
            formatted_lines.append(f'<div style="background:var(--mint);color:var(--ink);padding:2px 8px;font-family:var(--font-mono);font-size:12px;white-space:pre-wrap;">{escaped}</div>')
        elif l.startswith("-") and not l.startswith("---"):
            formatted_lines.append(f'<div style="background:var(--salmon);color:var(--ink);padding:2px 8px;font-family:var(--font-mono);font-size:12px;white-space:pre-wrap;">{escaped}</div>')
        elif l.startswith("@@"):
            formatted_lines.append(f'<div style="background:var(--canvas);color:var(--text-muted);font-weight:700;padding:4px 8px;font-family:var(--font-mono);font-size:12px;">{escaped}</div>')
        else:
            formatted_lines.append(f'<div style="background:var(--surface);color:var(--ink);padding:2px 8px;font-family:var(--font-mono);font-size:12px;white-space:pre-wrap;">{escaped}</div>')

    viewer_html = (
        '<div style="background:var(--surface);border:2px solid var(--ink);border-radius:8px;overflow:hidden;margin:1rem 0;">'
        + '<div style="background:var(--canvas);border-bottom:2px solid var(--ink);padding:8px 14px;display:flex;justify-content:space-between;align-items:center;">'
        + f'<span style="font-family:var(--font-mono);font-weight:700;font-size:13px;color:var(--ink);">{filename}</span>'
        + '<div style="font-family:var(--font-mono);font-size:12px;font-weight:700;">'
        + f'<span style="color:var(--green);">+{additions}</span>'
        + '<span style="color:var(--text-muted);"> · </span>'
        + f'<span style="color:var(--error-text);">−{deletions}</span>'
        + '</div></div>'
        + '<div style="max-height:420px;overflow-y:auto;overflow-x:auto;padding:4px 0;">'
        + ''.join(formatted_lines)
        + '</div></div>'
    )
    st.markdown(viewer_html, unsafe_allow_html=True)


# ─── Test Status Chip (§3.10) ──────────────────────────────────────────────

def render_test_status_chip(status: str = "not_run", command: str = "pytest -x", limits: str = "30s, 512 MB", timestamp: str = ""):
    """
    Renders Solo Ledger Test Status Chip (§3.10):
    ○ NOT RUN, ◌ RUNNING, ✓ PASSED, ✕ FAILED, ⊘ UNAVAILABLE.
    """
    s = status.lower()
    if s == "passed":
        chip = '<span class="pill pill-green">✓ PASSED</span>'
        desc = f"Executed in isolated runner{f' at {timestamp}' if timestamp else ''}. All assertions verified."
    elif s == "failed":
        chip = '<span class="pill" style="color:var(--error-text);border-color:var(--error-text);background:var(--salmon);">✕ FAILED</span>'
        desc = "Executed; non-zero exit code. Review output below."
    elif s == "running":
        chip = '<span class="pill" style="color:var(--link);border-color:var(--link);background:var(--surface);">◌ RUNNING</span>'
        desc = f"Executing `{command}`. Limits: {limits}."
    elif s == "unavailable":
        chip = '<span class="pill" style="color:var(--text-muted);border:1.5px dashed var(--text-muted);background:transparent;">⊘ UNAVAILABLE</span>'
        desc = "No isolated runner configured. Static review only."
    else:
        chip = '<span class="pill" style="color:var(--text-muted);border:1.5px dashed var(--text-muted);background:transparent;">○ NOT RUN</span>'
        desc = f"No tests were executed. Review is static. Configured command: `{command}` (Limits: {limits})."

    chip_html = (
        '<div style="display:inline-flex;align-items:center;gap:10px;background:var(--surface);border:1.5px solid var(--ink);border-radius:8px;padding:6px 12px;margin:6px 0;">'
        + f'{chip}'
        + f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">{desc}</span>'
        + '</div>'
    )
    st.markdown(chip_html, unsafe_allow_html=True)


# ─── Leaderboard Row (§513) ────────────────────────────────────────────────

def render_leaderboard_row(rank: int, display_name: str, level: int, xp: int, delta: str = "– 0", is_current_user: bool = False):
    """
    Renders Solo Ledger Leaderboard Row (§513):
    Row height ~56px, 1px --rule divider, rank in mono 800 (01, 02).
    Current user's row: --mint fill + 2px ink border + YOU pill.
    """
    rank_str = f"{rank:02d}"
    bg_style = "background:var(--mint);border:2px solid var(--ink);" if is_current_user else "background:var(--surface);border-bottom:1px solid var(--rule);"
    initial = display_name[0].upper() if display_name else "U"
    you_pill = '<span class="pill pill-green" style="font-size:9px;padding:1px 6px;margin-left:6px;">YOU</span>' if is_current_user else ""

    delta_color = "var(--green)" if delta.startswith("▲") else ("var(--error-text)" if delta.startswith("▼") else "var(--text-muted)")

    row_html = (
        f'<div style="{bg_style}border-radius:8px;padding:10px 16px;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between;gap:12px;">'
        + '<div style="display:flex;align-items:center;gap:14px;min-width:0;">'
        + f'<span style="font-family:var(--font-mono);font-size:18px;font-weight:800;color:var(--ink);width:32px;">{rank_str}</span>'
        + f'<div style="width:34px;height:34px;border-radius:50%;background:var(--canvas);border:1.5px solid var(--ink);display:grid;place-items:center;font-family:var(--font-mono);font-weight:800;font-size:13px;flex-shrink:0;">{initial}</div>'
        + '<div style="min-width:0;">'
        + f'<div style="font-family:var(--font-sans);font-weight:700;font-size:14px;color:var(--ink);display:flex;align-items:center;">{display_name} {you_pill}</div>'
        + f'<div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">LVL {level:02d}</div>'
        + '</div></div>'
        + '<div style="text-align:right;flex-shrink:0;">'
        + f'<div style="font-family:var(--font-mono);font-weight:800;font-size:15px;color:var(--ink);">{xp:,} XP</div>'
        + f'<div style="font-family:var(--font-mono);font-size:11px;color:{delta_color};">{delta}</div>'
        + '</div></div>'
    )
    st.markdown(row_html, unsafe_allow_html=True)


# ─── Achievement Badge (§518) ──────────────────────────────────────────────

def render_achievement_badge(name: str, desc: str, earned: bool, earned_date: str = "", category: str = "mint"):
    """
    Renders Solo Ledger Achievement Badge (§518):
    Earned: 96x96 circle, 2px ink border, pastel fill, check pill.
    Locked: 2px dashed border, --surface fill, lock icon, requirement.
    """
    if earned:
        border_style = "border:2px solid var(--ink);background:var(--" + category + ");"
        icon_symbol = "★"
        pill = '<span class="pill pill-green" style="font-size:9px;">✓ EARNED</span>'
        date_str = f'<div style="font-family:var(--font-mono);font-size:10px;color:var(--text-muted);margin-top:2px;">{earned_date}</div>' if earned_date else ""
    else:
        border_style = "border:2px dashed var(--dash);background:var(--surface);"
        icon_symbol = "⊘"
        pill = '<span class="pill" style="color:var(--text-muted);border:1px dashed var(--text-muted);font-size:9px;">LOCKED</span>'
        date_str = ""

    badge_html = (
        '<div class="rc-card" style="text-align:center;padding:16px;">'
        + f'<div style="width:72px;height:72px;border-radius:50%;{border_style}display:grid;place-items:center;margin:0 auto 10px auto;font-size:24px;color:var(--ink);">{icon_symbol}</div>'
        + f'<div style="font-family:var(--font-sans);font-weight:700;font-size:13px;color:var(--ink);margin-bottom:4px;">{name}</div>'
        + f'<div style="font-family:var(--font-sans);font-size:11px;color:var(--text-muted);line-height:1.3;margin-bottom:8px;min-height:30px;">{desc}</div>'
        + f'{pill}'
        + f'{date_str}'
        + '</div>'
    )
    st.markdown(badge_html, unsafe_allow_html=True)


# ─── Sidebar Navigation (§3.2) ─────────────────────────────────────────────

def render_sidebar_nav(current_page: str = ""):
    """
    Renders the Solo Ledger sidebar (§3.2):
    - Logo + wordmark: ◎ RepoCompass (Space Grotesk 700, 20px)
    - Flat 2px ink outlines, --mint active highlight with glyph ▸
    - Active repo chip with live/cached indicator
    - Profile card with avatar & Sign Out
    """
    with st.sidebar:
        # Wordmark (§3.2)
        st.markdown(
            '<div style="margin-bottom:1.25rem;border-bottom:2px solid var(--ink);padding-bottom:1rem;">'
            + '<div style="display:flex;align-items:center;gap:10px;">'
            + '<div style="width:34px;height:34px;border:2px solid var(--ink);border-radius:8px;background:var(--mint);display:grid;place-items:center;font-size:16px;font-weight:800;color:var(--ink);">◎</div>'
            + '<div><div style="font-family:var(--font-sans);font-size:18px;font-weight:700;color:var(--ink);line-height:1.2;">RepoCompass</div>'
            + '<div style="font-family:var(--font-mono);font-size:10px;font-weight:600;letter-spacing:0.08em;color:var(--text-muted);text-transform:uppercase;">Solo Ledger v1.0</div>'
            + '</div></div></div>',
            unsafe_allow_html=True
        )

        nav_items = [
            ("dashboard", "▣ Dashboard", "pages/02_dashboard.py"),
            ("explore", "⌕ Explore Repos", "pages/03_explore.py"),
            ("learning", "✎ My Learning", "pages/04_learning.py"),
            ("practice", "⚒ Practice Lab", "pages/05_practice.py"),
            ("leaderboard", "♛ Leaderboard", "pages/06_leaderboard.py"),
            ("maintainer", "✦ Maintainer Studio", "pages/07_maintainer.py"),
            ("sakura_trail", "🌸 Sakura Trail Arcade", "pages/09_sakura_trail.py"),
            ("settings", "⚙ Settings", "pages/08_settings.py"),
        ]

        curr_clean = current_page.lower().replace(" ", "_")

        for key, label, page in nav_items:
            is_active = (curr_clean == key)
            prefix = "▸ " if is_active else ""
            display_label = f"{prefix}{label}"

            if st.button(display_label, key=f"nav_{key}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.switch_page(page)

        # Active Repository (§3.2)
        active_repo = get_active_repo()
        active_name = active_repo.get("full_name", "No repo selected") if active_repo else "No repo selected"
        freshness_glyph = "● live" if active_repo else "○ none"

        st.markdown(
            '<div style="margin-top:1.5rem;padding-top:1rem;border-top:1px solid var(--rule);">'
            + '<div class="t-eyebrow" style="color:var(--text-muted);margin-bottom:6px;">ACTIVE REPOSITORY</div>'
            + '<div style="background:var(--canvas);border:1.5px solid var(--ink);border-radius:8px;padding:8px 12px;display:flex;justify-content:space-between;align-items:center;">'
            + f'<span style="font-family:var(--font-mono);font-size:12px;font-weight:600;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{active_name}</span>'
            + f'<span style="font-family:var(--font-mono);font-size:10px;color:var(--green);font-weight:600;">{freshness_glyph}</span>'
            + '</div></div>',
            unsafe_allow_html=True
        )

        user = get_current_user()
        if user:
            disp_name = user.get("display_name", "Contributor")
            initial = disp_name[0].upper() if disp_name else "C"
            st.markdown(
                '<div style="margin-top:1.25rem;background:var(--surface);border:2px solid var(--ink);border-radius:12px;padding:10px;display:flex;align-items:center;gap:10px;">'
                + f'<div style="width:36px;height:36px;border-radius:50%;background:var(--mint);border:2px solid var(--ink);color:var(--ink);font-weight:800;font-family:var(--font-mono);display:grid;place-items:center;font-size:14px;flex-shrink:0;">{initial}</div>'
                + '<div style="flex:1;min-width:0;">'
                + f'<div style="font-family:var(--font-sans);font-size:13px;font-weight:700;color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{disp_name}</div>'
                + f'<div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">LVL {user.get("level", 1):02d} · {user.get("xp", 0):,} XP</div>'
                + '</div></div>',
                unsafe_allow_html=True
            )

            if st.button("🚪 Sign Out", key="nav_signout_solo", use_container_width=True):
                clear_current_user()
                st.switch_page("streamlit_app.py")
        else:
            if st.button("🔑 Sign In", key="nav_signin_solo", use_container_width=True):
                st.switch_page("streamlit_app.py")

        st.markdown(
            '<div style="margin-top:1rem;padding:0.2rem;color:#64748B;font-size:0.72rem;display:flex;align-items:center;gap:6px;">'
            + '<span>RepoCompass v1.2</span> · <span>Zero-Trust Sandbox</span></div>',
            unsafe_allow_html=True
        )


def render_social_login_buttons():
    """
    Renders official GitHub and Google sign-in buttons with their real SVG logos.
    """
    st.markdown(
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:1rem;">'
        + '<div class="social-btn social-btn-github" style="pointer-events:none;">'
        + '<svg width="20" height="20" viewBox="0 0 98 96" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.59 2.934-16.42-5.867-16.42-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.074-6.6-10.839-1.141-22.243-5.378-22.243-24.283 0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.304.89 2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691C97.707 22 75.788 0 48.854 0z" fill="#fff"/></svg>'
        + '<span>Continue with GitHub</span></div>'
        + '<div class="social-btn social-btn-google" style="pointer-events:none;">'
        + '<svg width="20" height="20" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>'
        + '<span>Continue with Google</span></div></div>',
        unsafe_allow_html=True
    )


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
