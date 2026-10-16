"""
My Learning — Issue-to-code trail (Issue → File → Symbol → Test) and 5-Level Adaptive Hints.
"""
import streamlit as st

st.set_page_config(
    page_title="RepoCompass — Learning",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
for mod in list(sys.modules.keys()):
    if mod.startswith("app."):
        del sys.modules[mod]

from app.ui.shared import (
    inject_global_css, require_auth, render_sidebar_nav,
    render_top_status_bar, render_page_header,
    render_hint_box, render_code_trail_chain, render_status_pill,
    clean_html,
)
from app.ui.icons import icon
from app.services.code_search import search_code_for_issue
from app.services.hint_engine import generate_adaptive_hint, stream_adaptive_hint
from app.services.llm_service import (
    generate_json, build_code_trail_prompt,
    SYSTEM_PROMPT, check_ollama_available, LLMUnavailableError, LLMOutputError,
)
from app.services.reward_service import award_xp
from app.db.session import get_db
from app.db.models import Profile, PracticeSession
import uuid
from datetime import datetime, timezone

inject_global_css()
render_top_status_bar(is_live=True)
render_sidebar_nav("learning")

user = require_auth()
if not user:
    st.stop()

user_id = user["id"]
ollama_ok = check_ollama_available()

# ─── Page Title Header (§3.3) ──────────────────────────────────────────────

render_page_header(
    "My Learning",
    "Code Trail & Adaptive Hints",
    caption="Issue → File → Symbol → Test Trail · 5-Level Progressive Hint Ladder"
)

issue = st.session_state.get("active_issue")
repo_data = st.session_state.get("active_repo_data")

if not issue:
    # Show recent practice sessions from DB for continuity
    from app.db.models import Issue as IssueModel, Repository as RepoModel
    with get_db() as session:
        recent_sessions = (
            session.query(PracticeSession, IssueModel, RepoModel)
            .outerjoin(IssueModel, PracticeSession.issue_id == IssueModel.id)
            .join(RepoModel, PracticeSession.repository_id == RepoModel.id)
            .filter(PracticeSession.user_id == user_id)
            .order_by(PracticeSession.started_at.desc())
            .limit(5)
            .all()
        )
        session_list = [
            {
                "id": ps.id,
                "issue_title": iss.title if iss else "Practice Session",
                "issue_number": iss.number if iss else 0,
                "repo_name": repo.full_name if repo else "Unknown",
                "status": ps.status or "active",
                "started": ps.started_at.strftime("%b %d, %H:%M") if ps.started_at else "Recently",
            }
            for ps, iss, repo in recent_sessions
        ]

    st.markdown(clean_html("""
    <div class="rc-card card--tan" style="padding:20px;margin-bottom:1.5rem;">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
            <span style="font-size:20px;">📖</span>
            <span class="t-h3" style="color:var(--ink);">No issue selected</span>
        </div>
        <div style="font-family:var(--font-sans);font-size:14px;color:var(--ink);line-height:1.6;">
            Go to <strong>Explore Repositories</strong>, select an issue, and click <strong>View Code Trail</strong> to begin your guided learning path.
        </div>
    </div>
    """), unsafe_allow_html=True)

    if session_list:
        st.markdown(clean_html("""
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">
            <h3 style="font-family:var(--font-sans);font-size:18px;font-weight:700;color:var(--ink);margin:0;">
                Recent Learning Sessions <span style="font-weight:400;color:var(--text-muted);font-size:15px;">/ History</span>
            </h3>
        </div>
        """), unsafe_allow_html=True)

        for s in session_list:
            pill = render_status_pill(s["status"])
            st.markdown(clean_html(f"""
            <div class="rc-card" style="padding:12px 16px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <span style="font-family:var(--font-mono);font-size:12px;font-weight:700;color:var(--ink);">#{s['issue_number']}</span>
                        <span style="font-family:var(--font-sans);font-size:13px;font-weight:600;color:var(--ink);margin-left:8px;">{s['issue_title']}</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:10px;">
                        {pill}
                        <span style="font-family:var(--font-mono);font-size:10px;color:var(--text-muted);">{s['started']}</span>
                    </div>
                </div>
                <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-top:4px;">{s['repo_name']}</div>
            </div>
            """), unsafe_allow_html=True)

    if st.button("Go to Explore →", type="primary"):
        st.switch_page("pages/03_explore.py")
    st.stop()

# ─── Issue Summary Card (§3.8) ─────────────────────────────────────────────

labels_html = " ".join(
    f'<span class="pill pill-neutral" style="font-size:9px;">{l}</span>'
    for l in issue.get('labels', [])[:5]
)

st.markdown(clean_html(f"""
<div class="rc-card" style="margin-bottom:1.5rem;background:var(--surface);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:1.5rem;flex-wrap:wrap;">
        <div style="flex:1;min-width:280px;">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                <span class="t-eyebrow" style="color:var(--text-muted);">ACTIVE TARGET ISSUE</span>
                <span class="pill pill-green">#{issue.get('number')}</span>
                {labels_html}
            </div>
            <div class="t-h3" style="color:var(--ink);margin-bottom:6px;">
                {issue.get('title')}
            </div>
            <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);">
                REPOSITORY: {repo_data.get('full_name', 'Unknown') if repo_data else 'Active Repo'}
            </div>
        </div>
        <div style="flex-shrink:0;">
            <a href="{issue.get('html_url', '#')}" target="_blank" rel="noopener noreferrer" style="display:inline-flex;align-items:center;gap:6px;font-family:var(--font-mono);font-size:12px;font-weight:700;color:var(--ink);background:var(--canvas);border:1.5px solid var(--ink);border-radius:6px;padding:6px 12px;text-decoration:none;">
                ↗ View on GitHub
            </a>
        </div>
    </div>
</div>
"""), unsafe_allow_html=True)

left, right = st.columns([3, 2])

# ── Issue → Code Trail ───────────────────────────────────────────────────
with left:
    map_svg = icon("map", 18, "#17243D")
    st.markdown(f'<div class="section-title" style="display:flex;align-items:center;gap:6px;">{map_svg} <span>Issue → Code Trail</span></div>', unsafe_allow_html=True)
    st.markdown(clean_html("""
<div class="alert-info" style="margin-bottom:1rem;font-size:0.85rem;">
Maps this issue directly into <strong>File → Symbol → Test</strong>. 
Direct matches from error messages and identifiers are prioritized over AI inferences.
</div>
"""), unsafe_allow_html=True)

    trail_key = f"code_trail_{issue.get('number')}"

    # Auto-run deterministic trail if not yet run
    tree = repo_data.get("tree", []) if repo_data else []
    if trail_key not in st.session_state and tree:
        results = search_code_for_issue(
            issue_title=issue.get("title", ""),
            issue_body=issue.get("body", ""),
            directory_tree=tree,
        )
        st.session_state[trail_key] = {
            "relevant_files": results,
            "no_strong_match": len(results) == 0,
            "source": "deterministic",
        }

    col_det, col_ai = st.columns(2)
    with col_det:
        if st.button("Refresh Code Trail", type="secondary", key="trail_det_btn", use_container_width=True):
            with st.spinner("Analyzing codebase…"):
                results = search_code_for_issue(
                    issue_title=issue.get("title", ""),
                    issue_body=issue.get("body", ""),
                    directory_tree=tree,
                )
                st.session_state[trail_key] = {
                    "relevant_files": results,
                    "no_strong_match": len(results) == 0,
                    "source": "deterministic",
                }
                st.rerun()

    with col_ai:
        if st.button("Enhance with AI", key="trail_btn", disabled=not ollama_ok,
                     help="Requires Ollama running", use_container_width=True):

            tree_text = "\n".join(
                item["path"] for item in tree[:250] if item.get("type") == "blob"
            )
            prompt = build_code_trail_prompt(
                issue_title=issue.get("title", ""),
                issue_body=issue.get("body", ""),
                file_tree=tree_text,
            )
            with st.spinner("Analyzing issue context with Ollama…"):
                try:
                    ai_trail = generate_json(
                        prompt, system=SYSTEM_PROMPT,
                        schema_keys=["relevant_files"],
                    )
                    ai_files = ai_trail.get("relevant_files", [])
                    st.session_state[trail_key] = {
                        "relevant_files": ai_files,
                        "no_strong_match": len(ai_files) == 0,
                        "source": "ai",
                    }
                    st.rerun()
                except (LLMUnavailableError, LLMOutputError, Exception) as e:
                    st.error(f"Could not generate AI code trail: {e}")

    trail_data = st.session_state.get(trail_key)
    if trail_data:
        if trail_data.get("no_strong_match"):
            st.markdown(clean_html("""
<div style="background:var(--salmon);border:2px solid var(--ink);border-radius:10px;padding:14px;margin:1rem 0;">
    <div class="t-eyebrow" style="color:var(--ink);margin-bottom:6px;">○ NO STRONG DIRECT MATCH</div>
    <div style="font-family:var(--font-sans);font-size:13px;color:var(--ink);">
        No direct file or symbol references were found in the repository tree for this issue. 
        This may indicate a feature addition or cross-cutting configuration change.
    </div>
</div>
"""), unsafe_allow_html=True)
        else:
            files = trail_data.get("relevant_files", [])
            if not files:
                st.info("No relevant files identified.")
            else:
                st.markdown(f"**{len(files)} grounded code trail(s) mapped:**")
                st.session_state["trail_files"] = [f["path"] for f in files]

                for f in files:
                    conf = f.get("confidence", "low")
                    match_type = f.get("match_type", "ai_inferred")
                    path = f.get("path", "unknown")
                    reason = f.get("reason", "")
                    test_path = f.get("test_path")
                    symbols = f.get("symbols", [])

                    repo_url = repo_data.get("url", "") if repo_data else ""
                    file_url = f"{repo_url}/blob/HEAD/{path}" if repo_url else "#"
                    test_url = f"{repo_url}/blob/HEAD/{test_path}" if test_path and repo_url else None

                    match_mapped = "direct" if match_type == "direct_match" else ("related" if match_type == "related_reference" else "ai")

                    chain_nodes = [
                        {
                            "type": "ISSUE",
                            "name": f"#{issue.get('number')}",
                            "match": "direct",
                            "reason": issue.get("title", "")[:45] + "…",
                            "url": issue.get("html_url"),
                        },
                        {
                            "type": "FILE",
                            "name": path,
                            "match": match_mapped,
                            "reason": reason or "Identified from repository manifest or keywords.",
                            "url": file_url,
                        },
                        {
                            "type": "SYMBOL",
                            "name": ", ".join(symbols[:2]) if symbols else "(module scope)",
                            "match": "direct" if symbols else "not_found",
                            "reason": "Referenced symbol or function." if symbols else "No specific exported symbol identified.",
                            "url": None,
                        },
                        {
                            "type": "TEST",
                            "name": test_path if test_path else "(none found)",
                            "match": "related" if test_path else "not_found",
                            "reason": "Associated regression test suite." if test_path else "No direct unit/regression test matched.",
                            "url": test_url,
                        },
                    ]
                    render_code_trail_chain(chain_nodes)


# ── Adaptive Hints (§3.9.1) ─────────────────────────────────────────────────
with right:
    st.markdown('<div class="t-eyebrow" style="color:var(--text-muted);margin-bottom:4px;">PROGRESSIVE HINT LADDER</div>', unsafe_allow_html=True)
    st.markdown('<div class="t-h3" style="color:var(--ink);margin-bottom:8px;">5-Level Adaptive Stepper</div>', unsafe_allow_html=True)

    # Get experience level
    with get_db() as session:
        profile = session.query(Profile).filter_by(user_id=user_id).first()
        exp_level = (profile.experience_level if profile and profile.experience_level else "beginner").lower()

    hint_key = f"hints_{issue.get('number')}"
    if hint_key not in st.session_state:
        st.session_state[hint_key] = []

    hints = st.session_state[hint_key]
    current_level = len(hints)
    max_level = 5

    level_names = {
        1: "Concept",
        2: "Module",
        3: "File",
        4: "Function/Test",
        5: "Approach",
    }

    # Horizontal stepper display (§3.9.1)
    stepper_segments = []
    for lvl in range(1, max_level + 1):
        name = level_names[lvl]
        if lvl <= current_level:
            stepper_segments.append(f'<span style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--ink);background:var(--mint);border:1.5px solid var(--ink);padding:2px 8px;border-radius:4px;">LVL {lvl} ✓ {name}</span>')
        elif lvl == current_level + 1:
            stepper_segments.append(f'<span style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--ink);background:var(--salmon);border:1.5px solid var(--ink);padding:2px 8px;border-radius:4px;">LVL {lvl} ◌ {name}</span>')
        else:
            stepper_segments.append(f'<span style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);border:1px dashed var(--text-muted);padding:2px 8px;border-radius:4px;">LVL {lvl} ○ {name}</span>')

    st.markdown(clean_html(f"""
    <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin:10px 0 14px 0;">
        {' ── '.join(stepper_segments)}
    </div>
    """), unsafe_allow_html=True)

    # Render revealed hints
    for i, hint_text in enumerate(hints):
        render_hint_box(hint_text, i + 1)

    # Reveal next hint
    if current_level < max_level:
        next_level = current_level + 1
        next_desc = level_names.get(next_level, "")

        st.markdown(clean_html(f"""
        <div style="font-family:var(--font-sans);font-size:13px;color:var(--text-muted);margin:12px 0 6px 0;font-style:italic;">
            Want to try first? Write down what you'd check, then reveal the next level whenever you like.
        </div>
        """), unsafe_allow_html=True)

        if st.button(f"REVEAL LEVEL {next_level} HINT ({next_desc.upper()}) →", type="primary", use_container_width=True, key=f"hint_btn_{next_level}"):
            trail_files = st.session_state.get("trail_files", [])
            try:
                streamed = st.write_stream(
                    stream_adaptive_hint(
                        issue=issue,
                        hint_level=next_level,
                        relevant_files=trail_files,
                        exp_level=exp_level,
                        repo_data=repo_data,
                    )
                )
                new_hint = streamed if isinstance(streamed, str) else "".join(streamed or [])
            except Exception as e:
                st.error(f"Could not generate hint: {e}")
                new_hint = ""

            new_hint = (new_hint or "").strip()
            if new_hint:
                hints.append(new_hint)
                st.session_state[hint_key] = hints

                try:
                    with get_db() as session:
                        repo_id = repo_data.get("repo_id") if repo_data else None
                        issue_id = issue.get("id")
                        ps = (
                            session.query(PracticeSession)
                            .filter_by(user_id=user_id, issue_id=issue_id)
                            .first()
                        )
                        if ps:
                            ps.hint_level_reached = next_level
                            ps.hints_used = hints
                        else:
                            ps = PracticeSession(
                                id=str(uuid.uuid4()),
                                user_id=user_id,
                                issue_id=issue_id,
                                repository_id=repo_id or str(uuid.uuid4()),
                                hint_level_reached=next_level,
                                hints_used=hints,
                                status="active",
                            )
                            session.add(ps)
                except Exception:
                    pass

                st.rerun()
    else:
        st.markdown(clean_html("""
<div class="rc-card card--mint" style="padding:14px;margin-top:12px;">
    <div class="t-eyebrow" style="color:var(--ink);margin-bottom:4px;">✦ ALL 5 LEVELS UNLOCKED</div>
    <div style="font-family:var(--font-sans);font-size:13px;color:var(--ink);">
        You have unlocked all conceptual and structural hints. Ready to test your patch in the Practice Lab!
    </div>
</div>
"""), unsafe_allow_html=True)

    st.markdown(clean_html("""
    <div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-top:12px;">
        RULE · Per PRD principles, zero XP is deducted or awarded for requesting hints.
    </div>
    """), unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
    if st.button("OPEN PRACTICE LAB ⚒ →", type="primary", use_container_width=True, key="go_practice"):
        st.session_state["active_issue"] = issue
        st.session_state["active_repo_data"] = repo_data
        st.switch_page("pages/05_practice.py")


