"""
Practice Lab — Phase 6 Safe Simulation Workspace:
  - Monaco IDE Editor & Unified Diff Visualizer
  - Isolated Runner Integration with Path Traversal Security
  - Truthful Execution Status (Not run, Running, Passed, Failed, Unavailable)
  - Static AI Review and Pre-filled Git PR Assistant
"""
import streamlit as st
import streamlit.components.v1 as components
import html
import json
import re

st.set_page_config(
    page_title="RepoCompass — Practice Lab",
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
    render_diff_viewer, render_test_status_chip, render_ai_block,
    render_status_pill,
    clean_html,
)
from app.ui.icons import icon
from app.services.llm_service import (
    generate_stream, SYSTEM_PROMPT, check_ollama_available, LLMUnavailableError,
)
from app.services.reward_service import award_xp
from app.services.runner_service import (
    execute_patch_run, validate_patch_security, get_latest_run,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.db.models import PracticeSession, PracticeRun, Profile
from app.services.guide_generator import detect_repository_stack
import uuid
from datetime import datetime, timezone

inject_global_css()
render_top_status_bar(is_live=True)
render_sidebar_nav("practice")

user = require_auth()
if not user:
    st.stop()

user_id = user["id"]
settings = get_settings()
ollama_ok = check_ollama_available()

# ─── Page Title Header (§3.3) ──────────────────────────────────────────────

render_page_header(
    "Practice Lab",
    "Safe Simulation & Review",
    caption="Light Unified Diff · Patch Editor · Isolated Runner Quotas · Grounded Static AI Review"
)

issue = st.session_state.get("active_issue")
repo_data = st.session_state.get("active_repo_data")
trail_files = st.session_state.get("trail_files", [])

if not issue:
    st.info("No issue selected. Select an issue from **Explore Repositories** or **My Learning** first.")
    if st.button("Go to Explore", type="primary"):
        st.switch_page("pages/03_explore.py")
    st.stop()

stack = detect_repository_stack(repo_data or {})

# Runner status banner (§3.10)
if settings.runner_enabled:
    st.markdown(clean_html(f"""
<div class="rc-card card--mint" style="padding:12px 16px;margin-bottom:1.25rem;">
    <div style="display:flex;align-items:center;gap:10px;">
        <span class="pill pill-green">✓ ACTIVE RUNNER</span>
        <span style="font-family:var(--font-mono);font-size:12px;color:var(--ink);">Sandboxed container runner configured at <code>{settings.runner_base_url}</code></span>
    </div>
</div>
"""), unsafe_allow_html=True)
else:
    st.markdown(clean_html("""
<div class="rc-card card--tan" style="padding:12px 16px;margin-bottom:1.25rem;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
        <span class="pill pill-amber">⚠ ZERO-TRUST BOUNDARY</span>
        <span style="font-family:var(--font-sans);font-weight:700;font-size:13px;color:var(--ink);">Host Security Policy (PRD §5.8)</span>
    </div>
    <div style="font-family:var(--font-sans);font-size:12px;color:var(--ink);line-height:1.4;">
        Untrusted repository code is never executed directly on the host application server. 
        All reviews run in <strong>verified static review mode</strong> unless an isolated Docker runner is active.
    </div>
</div>
"""), unsafe_allow_html=True)

# ─── Load Saved Draft from DB ─────────────────────────────────────────────

patch_key = f"patch_{issue.get('number')}"
review_key = f"review_{issue.get('number')}"
session_id_key = f"session_id_{issue.get('number')}"

if patch_key not in st.session_state:
    try:
        with get_db() as session:
            ps = (
                session.query(PracticeSession)
                .filter_by(user_id=user_id, issue_id=str(issue.get("id")))
                .first()
            )
            if ps:
                st.session_state[patch_key] = ps.patch_draft or ""
                st.session_state[session_id_key] = ps.id
                if ps.ai_review:
                    st.session_state[review_key] = ps.ai_review
            else:
                st.session_state[patch_key] = ""
                st.session_state[session_id_key] = str(uuid.uuid4())
    except Exception:
        st.session_state[patch_key] = ""
        st.session_state[session_id_key] = str(uuid.uuid4())

curr_session_id = st.session_state.get(session_id_key, str(uuid.uuid4()))

# ─── Three-Panel Layout ───────────────────────────────────────────────────

panel_left, panel_mid, panel_right = st.columns([1.2, 1.8, 1.3])

# ─── Left Panel: Issue Context & Relevant Code Trail ──────────────────────
with panel_left:
    target_svg = icon("file_text", 18, "#17243D")
    st.markdown(f'<div class="section-title" style="margin-top:0;display:flex;align-items:center;gap:6px;">{target_svg} <span>Target Issue</span></div>', unsafe_allow_html=True)
    st.markdown(clean_html(f"""
<div class="rc-card" style="padding:1rem;">
    <div style="font-weight:700;color:#17243D;font-size:0.95rem;margin-bottom:0.4rem;">
        #{issue.get('number')} — {html.escape(issue.get('title', ''))}
    </div>
    <div style="font-size:0.82rem;color:#6B7890;line-height:1.55;max-height:180px;overflow-y:auto;background:#F8FAFC;padding:0.6rem;border-radius:6px;border:1px solid rgba(107,120,144,0.1);">
        {html.escape((issue.get('body') or 'No description provided.')[:800])}{'...' if len(issue.get('body') or '') > 800 else ''}
    </div>
    <div style="margin-top:0.6rem;display:flex;justify-content:space-between;align-items:center;">
        <span style="font-size:0.75rem;color:#6B7890;">State: <strong style="color:#21866D;">Open</strong></span>
        <a href="{issue.get('html_url', '#')}" target="_blank" style="font-size:0.75rem;color:#159A8C;text-decoration:none;">GitHub ↗</a>
    </div>
</div>
"""), unsafe_allow_html=True)

    if issue.get("labels"):
        st.markdown("**Labels:** " + " ".join(f"`{l}`" for l in issue["labels"][:5]))

    # Code Trail
    trail_svg = icon("map", 18, "#17243D")
    st.markdown(f'<div class="section-title" style="display:flex;align-items:center;gap:6px;">{trail_svg} <span>Relevant Files & Tests</span></div>', unsafe_allow_html=True)
    trail_key = f"code_trail_{issue.get('number')}"
    trail_data = st.session_state.get(trail_key)
    files = trail_data.get("relevant_files", []) if trail_data else []

    file_icon_svg = icon("file_text", 13, "#159A8C")
    sym_icon_svg = icon("settings", 12, "#7565C7")
    flask_icon_svg = icon("flask", 12, "#21866D")

    if files:
        for f in files[:4]:
            path = f.get("path", "")
            test_path = f.get("test_path")
            symbols = f.get("symbols", [])
            repo_url = repo_data.get("url", "") if repo_data else ""
            file_url = f"{repo_url}/blob/HEAD/{path}" if repo_url else "#"
            test_url = f"{repo_url}/blob/HEAD/{test_path}" if test_path and repo_url else "#"

            st.markdown(clean_html(f"""
<div style="padding:0.6rem;background:white;border:1px solid rgba(107,120,144,0.15);border-radius:8px;margin-bottom:0.5rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;">
        <code style="font-size:0.78rem;color:#159A8C;display:inline-flex;align-items:center;gap:3px;"><a href="{file_url}" target="_blank" style="color:#159A8C;text-decoration:none;">{file_icon_svg} <span>{path}</span></a></code>
        <span style="font-size:0.65rem;color:#21866D;font-weight:700;">{f.get('confidence', '').upper()}</span>
    </div>
    {f'<div style="font-size:0.72rem;color:#7565C7;margin-top:0.25rem;display:flex;align-items:center;gap:3px;">{sym_icon_svg} <span>Symbol: {symbols[0]}</span></div>' if symbols else ''}
    {f'<div style="font-size:0.72rem;color:#21866D;margin-top:0.2rem;display:flex;align-items:center;gap:3px;"><a href="{test_url}" target="_blank" style="color:#21866D;text-decoration:none;">{flask_icon_svg} <span>Test: {test_path} ↗</span></a></div>' if test_path else ''}
</div>
"""), unsafe_allow_html=True)
    elif trail_files:
        for f in trail_files[:5]:
            st.markdown(f'<code style="font-size:0.78rem;color:#159A8C;display:flex;align-items:center;gap:3px;padding:0.2rem 0;">{file_icon_svg} <span>{f}</span></code>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#6B7890;font-size:0.8rem;">Run code trail in My Learning to populate relevant files.</div>', unsafe_allow_html=True)

    # Acceptance Criteria & Testing
    test_svg = icon("flask", 18, "#17243D")
    st.markdown(f'<div class="section-title" style="display:flex;align-items:center;gap:6px;">{test_svg} <span>Target Test Suite</span></div>', unsafe_allow_html=True)
    st.markdown(clean_html(f"""
<div style="background:#F8FAFC;border:1px solid rgba(107,120,144,0.15);border-radius:8px;padding:0.75rem;">
    <div style="font-size:0.75rem;color:#6B7890;margin-bottom:0.3rem;">Automated runner command:</div>
    <code style="display:block;background:#101B35;color:#DDF7F3;padding:0.5rem;border-radius:6px;font-size:0.78rem;">{stack.get('test_command', 'pytest')}</code>
</div>
"""), unsafe_allow_html=True)


# ─── Middle Panel: Monaco IDE & Unified Diff Visualizer ──────────────────
with panel_mid:
    edit_svg = icon("edit", 18, "#17243D")
    st.markdown(f'<div class="section-title" style="margin-top:0;display:flex;align-items:center;gap:6px;">{edit_svg} <span>Proposed Patch / Solution</span></div>', unsafe_allow_html=True)

    # Template buttons
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        if st.button("Insert Diff Template", key="ins_diff", use_container_width=True):
            top_f = trail_files[0] if trail_files else "src/module.py"
            st.session_state[patch_key] = (
                f"--- a/{top_f}\n"
                f"+++ b/{top_f}\n"
                f"@@ -15,6 +15,9 @@\n"
                f" def target_function():\n"
                f"-    # Old problematic implementation\n"
                f"+    # Proposed bugfix addressing issue #{issue.get('number')}\n"
                f"+    if condition is None:\n"
                f"+        return fallback_value\n"
                f"     return standard_value\n"
            )
            st.rerun()

    with col_t2:
        if st.button("Insert Plan Template", key="ins_plan", use_container_width=True):
            st.session_state[patch_key] = (
                f"# Implementation Plan for Issue #{issue.get('number')}\n\n"
                f"1. **Root Cause Analysis:**\n"
                f"   - Identify where input is mishandled.\n\n"
                f"2. **Target File & Changes:**\n"
                f"   - File: {trail_files[0] if trail_files else 'src/module.py'}\n"
                f"   - Add defensive validation before processing.\n\n"
                f"3. **Regression Test Case:**\n"
                f"   - Add test case verifying fix with expected output.\n"
            )
            st.rerun()

    tab_monaco, tab_edit, tab_diff, tab_test_run = st.tabs([
        "Monaco IDE", "Standard Editor", "Unified Diff Preview", "Isolated Test Runner"
    ])


    current_patch = st.session_state.get(patch_key, "")

    # Tab 1: Monaco Editor
    with tab_monaco:
        lang_map = {
            "python": "python", "javascript": "javascript", "typescript": "typescript",
            "go": "go", "rust": "rust", "html": "html", "css": "css",
        }
        editor_lang = lang_map.get(stack.get("language", "").lower(), "python")

        monaco_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/editor/editor.main.min.css">
            <style>
                html, body {{ margin: 0; padding: 0; height: 100%; width: 100%; overflow: hidden; background: #101B35; border-radius: 8px; }}
                #container {{ height: 100%; width: 100%; }}
            </style>
        </head>
        <body>
            <div id="container"></div>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js"></script>
            <script>
                require.config({{ paths: {{ 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' }} }});
                require(['vs/editor/editor.main'], function() {{
                    var editor = monaco.editor.create(document.getElementById('container'), {{
                        value: {json.dumps(current_patch or '# Monaco IDE Editor ready\n# Enter unified diff or python solution...')},
                        language: '{editor_lang}',
                        theme: 'vs-dark',
                        automaticLayout: true,
                        fontSize: 13,
                        minimap: {{ enabled: false }},
                        scrollBeyondLastLine: false,
                        lineNumbers: 'on',
                    }});
                }});
            </script>
        </body>
        </html>
        """
        components.html(monaco_html, height=320)
        st.caption("Monaco IDE Editor with syntax coloring, line numbers, and theme support.")

    # Tab 2: Standard Editor
    with tab_edit:
        patch_text = st.text_area(
            "Patch Editor",
            value=current_patch,
            height=320,
            placeholder="# Write your unified diff or implementation plan here...",
            label_visibility="collapsed",
            key="patch_textarea",
        )
        st.session_state[patch_key] = patch_text

    # Tab 3: Unified Diff Preview (§3.10)
    with tab_diff:
        top_filename = trail_files[0] if trail_files else "patch.diff"
        render_diff_viewer(current_patch, filename=top_filename)

    # Tab 4: Isolated Test Runner & Sandbox Execution
    with tab_test_run:
        st.markdown("**Isolated Test Runner & Quotas:**")
        st.markdown(clean_html(f"""
<div style="font-size:0.8rem;color:#6B7890;margin-bottom:0.75rem;">
    • <strong>Sandbox Command:</strong> <code>{stack.get('test_command', 'pytest')}</code><br>
    • <strong>Quotas:</strong> Timeout: 30s | Memory: 512MB | CPU: 1 Core | Network Egress: Blocked<br>
    • <strong>Security Check:</strong> Traversal paths (<code>../</code>, root <code>/</code>) strictly prohibited.
</div>
"""), unsafe_allow_html=True)

        if st.button("Execute Run (Sandbox)", key="exec_run_btn", use_container_width=True):
            with st.spinner("Enforcing security boundaries and executing run…"):
                run_res = execute_patch_run(
                    session_id=curr_session_id,
                    repo_full_name=repo_data.get("full_name", ""),
                    patch_content=st.session_state.get(patch_key, ""),
                    test_command=stack.get("test_command", "pytest"),
                    user_id=user_id,
                )
                st.session_state[f"last_run_{issue.get('number')}"] = run_res

        last_run = st.session_state.get(f"last_run_{issue.get('number')}")
        status_val = last_run["status"] if last_run else "not_run"
        render_test_status_chip(status_val, command=stack.get("test_command", "pytest"), limits="30s, 512 MB")

        if last_run and last_run.get("output"):
            st.markdown(clean_html(f"""
<div style="background:var(--ink);border:2px solid var(--ink);border-radius:8px;padding:12px;margin-top:10px;font-family:var(--font-mono);">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;border-bottom:1px solid rgba(255,255,255,0.2);padding-bottom:4px;">
        <span style="color:var(--mint);font-size:12px;font-weight:700;">TEST RUNNER EXECUTION LOG</span>
        <span style="color:var(--surface);font-size:11px;">EXIT CODE: {last_run.get('exit_code', 0)}</span>
    </div>
    <pre style="color:var(--surface);font-size:11px;white-space:pre-wrap;margin:0;max-height:240px;overflow-y:auto;">{html.escape(last_run['output'])}</pre>
</div>
"""), unsafe_allow_html=True)

    # Action buttons (§3.4)
    col_save, col_rev, col_rst = st.columns([1, 1.2, 0.8])
    with col_save:
        if st.button("SAVE DRAFT", key="save_patch_btn", use_container_width=True):
            try:
                with get_db() as session:
                    repo_id = repo_data.get("repo_id") if repo_data else None
                    issue_id = str(issue.get("id"))
                    ps = (
                        session.query(PracticeSession)
                        .filter_by(user_id=user_id, issue_id=issue_id)
                        .first()
                    )
                    if ps:
                        ps.patch_draft = st.session_state.get(patch_key, "")
                    else:
                        ps = PracticeSession(
                            id=curr_session_id,
                            user_id=user_id,
                            issue_id=issue_id,
                            repository_id=repo_id or str(uuid.uuid4()),
                            patch_draft=st.session_state.get(patch_key, ""),
                            status="active",
                        )
                        session.add(ps)
                award_xp(user_id, "practice_session_started", idempotency_context=issue_id)
                st.toast("✓ Draft saved to local profile")
            except Exception as e:
                st.error(f"Save failed: {e}")

    with col_rev:
        rev_disabled = not st.session_state.get(patch_key, "").strip() or not ollama_ok
        review_slot = st.empty()
        if st.button("AI CODE REVIEW ✦", type="primary", disabled=rev_disabled, use_container_width=True, key="run_rev_btn"):
            prompt = f"""You are RepoCompass AI Tutor performing a static code review on a contributor's proposed patch.
Issue: #{issue.get('number')} — {issue.get('title')}
Issue Body: {(issue.get('body') or '')[:400]}

Proposed Patch or Plan:
{st.session_state.get(patch_key, '')[:2500]}

Relevant Code Trail Files: {', '.join(trail_files[:4]) if trail_files else 'Not specified'}

Provide a structured, helpful static code review:
1. **Approach & Correctness:** Does this proposed fix address the root problem?
2. **Edge Cases & Regressions:** What boundary conditions or potential side-effects should the author consider?
3. **Recommended Test Case:** Describe a test assertion to verify this fix in {stack.get('test_runner', 'pytest')}.

Remember: Do NOT claim tests have been executed. This is a static analysis review."""

            try:
                streamed = review_slot.write_stream(
                    generate_stream(prompt, system=SYSTEM_PROMPT, temperature=0.2)
                )
                review_result = streamed if isinstance(streamed, str) else "".join(streamed or [])
                if review_result.strip():
                    st.session_state[review_key] = review_result
                    award_xp(user_id, "practice_milestone", idempotency_context=f"rev_{issue.get('number')}")
                    st.rerun()
                else:
                    st.error("The model returned an empty review. Please try again.")
            except LLMUnavailableError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"Review error: {e}")

    with col_rst:
        if st.button("RESET", key="rst_btn", use_container_width=True):
            st.session_state.pop(patch_key, None)
            st.session_state.pop(review_key, None)
            st.rerun()

    # Truthful Test Status Note (§3.10)
    st.markdown("<br>", unsafe_allow_html=True)
    render_test_status_chip(status_val, command=stack.get("test_command", "pytest"), limits="30s, 512 MB")


# ─── Right Panel: AI Review, Checklist & Git Assistant ────────────────────
with panel_right:
    st.markdown('<div class="t-eyebrow" style="color:var(--text-muted);margin-bottom:6px;">STATIC AI REVIEW</div>', unsafe_allow_html=True)

    review_text = st.session_state.get(review_key)
    if review_text:
        render_ai_block(review_text, model="qwen3:4b", timestamp="14:32", sources=trail_files[:3])
    elif not ollama_ok:
        st.markdown(clean_html("""
        <div style="background:var(--salmon);border:1.5px solid var(--ink);border-radius:8px;padding:12px;font-family:var(--font-sans);font-size:12px;color:var(--ink);">
            ⚠ Ollama daemon offline — start <code>ollama serve</code> for automated static patch review.
        </div>
        """), unsafe_allow_html=True)
    else:
        st.markdown(clean_html("""
        <div style="background:var(--surface);border:2px dashed var(--ink);border-radius:8px;padding:16px;text-align:center;font-family:var(--font-sans);font-size:13px;color:var(--text-muted);">
            Draft your patch in the editor and click <strong>AI CODE REVIEW</strong> to receive architectural critique and regression checks.
        </div>
        """), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Interactive Checklist (§3.6)
    st.markdown('<div class="t-eyebrow" style="color:var(--text-muted);margin-bottom:6px;">CONTRIBUTION CHECKLIST</div>', unsafe_allow_html=True)
    checklist_items = [
        "Read project CONTRIBUTING guide",
        "Clone fork to local environment",
        "Create focused topic branch",
        "Implement minimal bugfix or feature",
        "Run automated tests locally",
        "Confirm no regression failures",
        "Commit with descriptive issue reference",
        "Push branch to remote fork",
        "Open Pull Request against upstream",
    ]

    chk_key = f"chk_{issue.get('number')}"
    if chk_key not in st.session_state:
        st.session_state[chk_key] = {item: False for item in checklist_items}

    for item in checklist_items:
        val = st.checkbox(item, value=st.session_state[chk_key].get(item, False), key=f"c_{item}_{issue.get('number')}")
        st.session_state[chk_key][item] = val

    done_count = sum(st.session_state[chk_key].values())
    pct = int(done_count / len(checklist_items) * 100)
    st.markdown(clean_html(f"""
<div style="margin-top:0.5rem;margin-bottom:1.5rem;">
    <div style="display:flex;justify-content:space-between;font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-bottom:4px;">
        <span>READINESS PROGRESS</span>
        <span>{done_count}/{len(checklist_items)} CHECKED</span>
    </div>
    <div class="ledger-progress-track">
        <div class="ledger-progress-fill" style="width:{pct}%;"></div>
    </div>
</div>
"""), unsafe_allow_html=True)

    # Git Assistant Pre-filled Commands (§3.6)
    clean_title = re.sub(r'[^a-zA-Z0-9\-]', '-', issue.get('title', '')).lower()[:28].strip('-')
    branch_name = f"fix/issue-{issue.get('number')}-{clean_title}"

    st.markdown('<div class="t-eyebrow" style="color:var(--text-muted);margin-bottom:6px;">GIT PR ASSISTANT</div>', unsafe_allow_html=True)
    st.markdown(clean_html(f"""
<div style="background:var(--canvas);border:2px solid var(--ink);border-radius:8px;padding:12px;font-family:var(--font-mono);font-size:11px;color:var(--ink);line-height:1.7;">
    <div style="color:var(--text-muted);"># 1. Create topic branch</div>
    git checkout -b {branch_name}<br>
    <div style="color:var(--text-muted);margin-top:6px;"># 2. Stage & commit</div>
    git commit -m "fix: #{issue.get('number')} {issue.get('title', '')[:40]}"<br>
    <div style="color:var(--text-muted);margin-top:6px;"># 3. Push to remote fork</div>
    git push origin {branch_name}
</div>
"""), unsafe_allow_html=True)

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)
    compare_url = issue.get("html_url", "#").split("/issues/")[0] + "/compare" if "/issues/" in issue.get("html_url", "") else issue.get("html_url", "#")
    st.link_button("OPEN GITHUB TO SUBMIT PR ↗", compare_url, use_container_width=True)

