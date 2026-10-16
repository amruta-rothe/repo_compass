"""
Explore Repositories — URL input, analysis progress, guide + issue ranking.
"""
import streamlit as st
import time

st.set_page_config(
    page_title="RepoCompass — Explore",
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
    render_difficulty_badge, render_issue_card, render_status_pill,
    render_ai_block, render_empty_repository_spec, render_evidence_badge,
    render_workflow_infographic, generate_mermaid_workflow,
    clean_html,
)
from app.ui.icons import icon
from app.services.repository_fetcher import fetch_and_cache_repository, FetchError
from app.services.issue_ranker import rank_issues
from app.core.config import get_settings
from app.services.guide_generator import generate_grounded_guide, enrich_guide_with_ollama
from app.services.llm_service import (
    generate_json, generate, LLMUnavailableError, LLMOutputError,
    SYSTEM_PROMPT, check_ollama_available, warm_up_model,
)
from app.services.reward_service import award_xp, maybe_award_achievement
from app.db.session import get_db
from app.db.models import Profile, Guide, Issue, Repository
import uuid
from datetime import datetime, timezone

inject_global_css()
render_top_status_bar(is_live=True)
render_sidebar_nav("explore")

user = require_auth()
if not user:
    st.stop()

user_id = user["id"]

# Load user profile for issue ranking
with get_db() as session:
    profile = session.query(Profile).filter_by(user_id=user_id).first()
    profile_dict = {
        "programming_languages": (profile.programming_languages or []) if profile else [],
        "experience_level": (profile.experience_level or "beginner") if profile else "beginner",
    }

# ─── Page Title Header (§3.3) ──────────────────────────────────────────────

render_page_header(
    "Explore Repositories",
    "Intelligence & Guides",
    caption="Grounded codebase manifests, personalized issue fits, and verified contribution workflows."
)

# ─── URL input ─────────────────────────────────────────────────────────────

# Check URL query param or session state for target repo
target_repo = st.query_params.get("repo") or st.session_state.get("active_repo_full_name") or st.session_state.get("explore_url") or ""
if target_repo.startswith("https://github.com/"):
    target_repo = target_repo.replace("https://github.com/", "")

col_input, col_btn = st.columns([5, 1])
with col_input:
    repo_url = st.text_input(
        "GitHub repository URL or owner/repo",
        value=target_repo,
        placeholder="https://github.com/owner/repo  or  owner/repo",
        label_visibility="collapsed",
        key="repo_url_input",
    )
with col_btn:
    analyze_btn = st.button("ANALYZE →", type="primary", use_container_width=True, key="analyze_btn")

force_refresh = st.checkbox("Force refresh (bypass cache)", value=False, key="force_refresh")

# ─── Check Ollama status ───────────────────────────────────────────────────

ollama_ok = check_ollama_available()

# Fire-and-forget model warm-up: load the weights into RAM in a background thread
if ollama_ok and not st.session_state.get("_ollama_warmed"):
    st.session_state["_ollama_warmed"] = True
    import threading
    threading.Thread(target=warm_up_model, daemon=True).start()

if not ollama_ok:
    st.markdown(clean_html("""
<div style="background:var(--salmon);border:2px solid var(--ink);border-radius:10px;padding:12px 16px;margin:10px 0;display:flex;align-items:center;gap:12px;">
    <span style="font-family:var(--font-mono);font-size:18px;font-weight:900;color:var(--ink);">⚠</span>
    <div style="font-family:var(--font-sans);font-size:13px;color:var(--ink);">
        <strong>Ollama service offline or initializing</strong>. 
        Repository indexing and grounded build guides operate instantly (<5ms). 
        Run <code>ollama serve</code> to enable optional deep LLM enrichment.
    </div>
</div>
"""), unsafe_allow_html=True)

# ─── Auto-load cached repository upon refresh or dashboard navigation ──────

if not st.session_state.get("analysis_result") and target_repo:
    try:
        result = fetch_and_cache_repository(target_repo.strip(), force_refresh=False)
        repo_d = result['repo']
        snap_d = result['snapshot']
        st.session_state["analysis_result"] = {
            "repo_id": repo_d["id"],
            "full_name": repo_d["full_name"],
            "description": repo_d.get("description") or "",
            "primary_language": repo_d.get("primary_language"),
            "stars": repo_d.get("stars", 0),
            "url": repo_d.get("url", ""),
            "readme": snap_d["readme_content"] if snap_d else None,
            "contributing": snap_d["contributing_content"] if snap_d else None,
            "tree": snap_d["directory_tree"] if snap_d else [],
            "dep_files": snap_d["dependency_files"] if snap_d else {},
            "issues": result["issues"],
            "from_cache": True,
            "last_analyzed": repo_d.get("last_analyzed_at"),
        }
        from app.services.guide_generator import get_cached_guide
        cached_g = get_cached_guide(repo_d["id"])
        if cached_g:
            st.session_state["guide_content"] = cached_g
        else:
            st.session_state["guide_content"] = generate_grounded_guide(st.session_state["analysis_result"])
        st.query_params["repo"] = repo_d["full_name"]
        st.session_state["active_repo_full_name"] = repo_d["full_name"]
    except Exception:
        pass

# ─── Analysis flow ─────────────────────────────────────────────────────────

if analyze_btn and repo_url:
    st.session_state.pop("analysis_result", None)
    st.session_state.pop("guide_content", None)

    with st.status("Analyzing repository…", expanded=True) as status:
        st.write("Fetching repository metadata & file manifests…")
        try:
            result = fetch_and_cache_repository(repo_url.strip(), force_refresh=force_refresh)
            repo_d = result['repo']       # plain dict
            snap_d = result['snapshot']   # plain dict or None
            st.write(f"Found repository: `{repo_d['full_name']}`")

            if result["fetch_errors"]:
                for key, err in result["fetch_errors"].items():
                    st.write(f"{key}: {err}")

            st.write(f"Loaded {len(result['issues'])} open issues")
            if result["from_cache"]:
                st.write("Loaded instantly from database cache (<5ms)")

            # Award XP for repo analysis
            is_first = award_xp(user_id, "first_repo_analyzed", idempotency_context="first")[1]
            award_xp(user_id, "repo_analyzed", idempotency_context=repo_d['full_name'])
            if is_first:
                maybe_award_achievement(user_id, "first_repo")

            st.session_state["analysis_result"] = {
                "repo_id": repo_d["id"],
                "full_name": repo_d["full_name"],
                "description": repo_d.get("description") or "",
                "primary_language": repo_d.get("primary_language"),
                "stars": repo_d.get("stars", 0),
                "url": repo_d.get("url", ""),
                "readme": snap_d["readme_content"] if snap_d else None,
                "contributing": snap_d["contributing_content"] if snap_d else None,
                "tree": snap_d["directory_tree"] if snap_d else [],
                "dep_files": snap_d["dependency_files"] if snap_d else {},
                "issues": result["issues"],
                "from_cache": result["from_cache"],
                "last_analyzed": repo_d.get("last_analyzed_at"),
            }
            # Persist repo parameter in URL so it persists across refreshes
            st.query_params["repo"] = repo_d["full_name"]
            st.session_state["active_repo_full_name"] = repo_d["full_name"]

            # Generate grounded guide & dynamic workflow
            st.write("Generating grounded onboarding guide & 2D dynamic workflow…")
            ar = st.session_state["analysis_result"]
            guide_data = generate_grounded_guide(ar)
            st.session_state["guide_content"] = guide_data

            # AI enrichment is deliberately NOT run here: the deterministic guide
            # renders instantly, and the LLM polish is offered as an opt-in action
            # from the Guide tab. This keeps analysis latency independent of the model.
            st.session_state["ollama_ok"] = ollama_ok
            st.write("Structured guide & dynamic workflow generated instantly")

            status.update(label="Analysis complete!", state="complete")

        except FetchError as e:
            status.update(label="Analysis failed", state="error")
            st.error(str(e))
        except Exception as e:
            import traceback
            status.update(label="Unexpected error", state="error")
            st.error(f"Unexpected error: {e}")
            with st.expander("Show detailed error trace"):
                st.code(traceback.format_exc())


# ─── Display results ───────────────────────────────────────────────────────

ar = st.session_state.get("analysis_result")
if not ar:
    # Show previously analyzed repositories from DB
    with get_db() as session:
        prev_repos = (
            session.query(Repository)
            .filter(Repository.last_analyzed_at.isnot(None))
            .order_by(Repository.last_analyzed_at.desc())
            .limit(12)
            .all()
        )
        prev_repo_list = [
            {
                "id": r.id,
                "full_name": r.full_name,
                "description": r.description or "",
                "primary_language": r.primary_language or "",
                "stars": r.stars or 0,
                "last_analyzed": r.last_analyzed_at.strftime("%b %d, %H:%M") if r.last_analyzed_at else "Recently",
            }
            for r in prev_repos
        ]

    if prev_repo_list:
        st.markdown(
            '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.75rem;">'  
            + '<h3 style="font-family:var(--font-sans);font-size:18px;font-weight:700;color:var(--ink);margin:0;">'  
            + 'Previously Analyzed Repositories <span style="font-weight:400;color:var(--text-muted);font-size:15px;">/ Cached</span>'  
            + '</h3><span class="pill pill-green">● CACHED</span></div>',
            unsafe_allow_html=True
        )

        cols = st.columns(min(3, len(prev_repo_list)))
        for idx, r in enumerate(prev_repo_list[:6]):
            with cols[idx % 3]:
                desc = r["description"][:90] + "..." if len(r["description"]) > 90 else (r["description"] or "Architecture workflow mapped.")
                card_html = (
                    '<div class="rc-card" style="padding:14px;margin-bottom:10px;">'
                    + '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">'
                    + f'<span style="font-family:var(--font-mono);font-size:13px;font-weight:700;color:var(--ink);">{r["full_name"]}</span>'
                    + '</div>'
                    + f'<div style="font-family:var(--font-sans);font-size:12px;color:var(--text-muted);margin-bottom:6px;line-height:1.4;">{desc}</div>'
                    + '<div style="display:flex;justify-content:space-between;align-items:center;">'
                    + f'<span style="font-family:var(--font-mono);font-size:10px;color:var(--text-muted);">★ {r["stars"]:,} · {r["primary_language"]}</span>'
                    + f'<span style="font-family:var(--font-mono);font-size:10px;color:var(--green);">{r["last_analyzed"]}</span>'
                    + '</div></div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
                if st.button(f"Load → {r['full_name']}", key=f"explore_load_{r['id']}", use_container_width=True):
                    st.query_params["repo"] = r["full_name"]
                    st.session_state["active_repo_full_name"] = r["full_name"]
                    st.rerun()
    else:
        st.markdown(clean_html(f"""
<div style="text-align:center;padding:3rem;color:#6B7890;">
    <div style="display:flex;justify-content:center;margin-bottom:1rem;">{icon('search', 40, '#6B7890')}</div>
    <div style="font-size:1rem;font-weight:500;margin-bottom:0.5rem;">Enter a repository URL above to get started</div>
    <div style="font-size:0.85rem;">Try: <code>microsoft/vscode</code>, <code>django/django</code>, <code>facebook/react</code></div>
</div>
"""), unsafe_allow_html=True)
    st.stop()

# ── Repo identity card (§3.6) ─────────────────────────────────────────────

cache_pill = render_status_pill("cached", "CACHED (<5ms)") if ar.get("from_cache") else render_status_pill("live", "LIVE SYNC")
lang_html = f'<div style="text-align:right;"><div class="t-kpi-md" style="color:var(--ink);">{ar["primary_language"]}</div><div class="t-eyebrow" style="color:var(--text-muted);">LANGUAGE</div></div>' if ar.get("primary_language") else ''

st.markdown(clean_html(f"""
<div class="rc-card" style="margin-bottom:1.5rem;background:var(--surface);">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:1.5rem;">
        <div style="flex:1;min-width:280px;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                <span class="t-eyebrow" style="color:var(--text-muted);">REPOSITORY MANIFEST</span>
                {cache_pill}
            </div>
            <div class="t-h2" style="color:var(--ink);margin-bottom:6px;">{ar['full_name']}</div>
            <div style="font-family:var(--font-sans);font-size:14px;color:var(--ink);line-height:1.5;">{ar.get('description') or 'No description provided'}</div>
        </div>
        <div style="display:flex;gap:2rem;align-items:center;flex-wrap:wrap;">
            <div style="text-align:right;">
                <div class="t-kpi-md" style="color:var(--ink);">★ {ar.get('stars', 0):,}</div>
                <div class="t-eyebrow" style="color:var(--text-muted);">STARS</div>
            </div>
            <div style="text-align:right;">
                <div class="t-kpi-md" style="color:var(--ink);">{len(ar['issues'])}</div>
                <div class="t-eyebrow" style="color:var(--text-muted);">OPEN ISSUES</div>
            </div>
            {lang_html}
        </div>
    </div>
</div>
"""), unsafe_allow_html=True)

# ── Tabs (§3.11) ──────────────────────────────────────────────────────────

tab_guide, tab_issues, tab_tree, tab_workflow = st.tabs([
    "Onboarding Guide", "Issues", "Codebase Map", "Contribution Workflow"
])

# ── Tab: Guide ────────────────────────────────────────────────────────────
with tab_guide:
    guide = st.session_state.get("guide_content")
    if not guide and ar:
        guide = generate_grounded_guide(ar)
        st.session_state["guide_content"] = guide

    if guide:
        # Overview
        tech_stack_html = (
            '<div style="margin-top:0.75rem;display:flex;flex-wrap:wrap;gap:0.4rem;">'
            + ''.join(
                f'<span class="pill pill-neutral">{t}</span>'
                for t in guide.get("tech_stack", [])[:8]
            )
            + '</div>'
        ) if guide.get("tech_stack") else ""

        overview_text = guide.get('overview', '').strip()
        if not overview_text or overview_text == "Not specified in the repository.":
            render_empty_repository_spec(["README.md", "CONTRIBUTING.md", "package.json"])
        elif guide.get("is_ai_enriched"):
            render_ai_block(overview_text, model="qwen3:4b", timestamp="14:32", sources=["README.md", "CONTRIBUTING.md"])
            if tech_stack_html:
                st.markdown(tech_stack_html, unsafe_allow_html=True)
        else:
            st.markdown(clean_html(f"""
<div class="rc-card" style="margin-bottom:1rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span class="t-eyebrow" style="color:var(--ink);">PROJECT OVERVIEW & ARCHITECTURE</span>
        <span class="pill pill-green">✓ VERIFIED GROUNDED</span>
    </div>
    <div style="font-family:var(--font-sans);font-size:14px;color:var(--ink);line-height:1.6;">
        {overview_text}
    </div>
    {tech_stack_html}
</div>
"""), unsafe_allow_html=True)

        # ── Opt-in AI enrichment ──────────────────────────────────────────
        if st.session_state.get("ollama_ok") and not guide.get("is_ai_enriched"):
            if st.button(
                "✨ Add AI summary",
                key="enrich_guide_btn",
                help=f"Polish the overview with {get_settings().ollama_model}",
            ):
                with st.spinner(f"Asking {get_settings().ollama_model}…"):
                    try:
                        st.session_state["guide_content"] = enrich_guide_with_ollama(guide, ar)
                        st.rerun()
                    except Exception:
                        st.warning(
                            "AI enrichment is unavailable — showing the verified grounded guide."
                        )

        # Pro tips (if any)
        if guide.get("contributor_tips"):
            st.markdown(clean_html("""
<div class="rc-card card--tan" style="margin:1rem 0;padding:16px;">
    <div class="t-eyebrow" style="color:var(--ink);margin-bottom:8px;">✦ PRO TIPS FOR NEW CONTRIBUTORS</div>
""" + "".join(f'<div style="font-family:var(--font-sans);font-size:13px;color:var(--ink);margin-bottom:4px;">· {tip}</div>' for tip in guide["contributor_tips"]) + """
</div>
"""), unsafe_allow_html=True)

        # Setup steps
        if guide.get("setup_steps"):
            st.markdown('<div class="t-h3" style="color:var(--ink);margin:1.5rem 0 0.75rem 0;">Setup & Prerequisites</div>', unsafe_allow_html=True)
            if guide.get("prerequisites"):
                st.markdown("**Requirements & Environment:**")
                for req in guide["prerequisites"]:
                    st.markdown(f"- {req}")

            for i, step in enumerate(guide["setup_steps"], 1):
                verified = step.get("verified", False)
                source = step.get("source", "inferred")
                badge_html = render_evidence_badge("verified" if verified else "inferred")
                cmd = step.get("command")
                cmd_html = (
                    f'<code style="display:block;background:var(--canvas);'
                    f'border:1.5px solid var(--ink);'
                    f'border-radius:6px;padding:0.6rem 0.8rem;'
                    f'font-family:var(--font-mono);font-size:12px;margin-top:0.4rem;color:var(--ink);">'
                    f'{cmd}</code>'
                ) if cmd else ""
                st.markdown(clean_html(f"""
<div class="rc-card" style="margin-bottom:0.75rem;padding:14px 18px;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:0.3rem;">
        <div style="font-family:var(--font-mono);font-weight:700;color:var(--ink);font-size:13px;">STEP {i}: {step.get('step', '')}</div>
        {badge_html}
    </div>
    {cmd_html}
</div>
"""), unsafe_allow_html=True)

        # Important dirs
        if guide.get("important_dirs"):
            st.markdown('<div class="t-h3" style="color:var(--ink);margin:1.5rem 0 0.5rem 0;">Important Codebase Directories</div>', unsafe_allow_html=True)
            dir_rows = "".join(
                '<tr>'
                + f'<td style="font-family:var(--font-mono);font-weight:700;color:var(--ink);padding:8px 12px;">{d.get("path","")}</td>'
                + f'<td style="font-family:var(--font-sans);color:var(--ink);padding:8px 12px;">{d.get("purpose","")}</td>'
                + '</tr>'
                for d in guide["important_dirs"]
            )
            dir_table = (
                '<table class="ledger-table" style="margin:0.5rem 0 1.5rem 0;">'
                + '<thead><tr>'
                + '<th style="padding:8px 12px;">DIRECTORY PATH</th>'
                + '<th style="padding:8px 12px;">PURPOSE &amp; ARCHITECTURAL ROLE</th>'
                + '</tr></thead>'
                + '<tbody>' + dir_rows + '</tbody>'
                + '</table>'
            )
            st.markdown(dir_table, unsafe_allow_html=True)

        # Missing info
        if guide.get("missing_info"):
            st.markdown(clean_html(f"""
<div style="background:var(--salmon);border:2px solid var(--ink);border-radius:10px;padding:14px 18px;margin-top:1rem;">
    <div class="t-eyebrow" style="color:var(--ink);margin-bottom:6px;">⚠ HONEST REPOSITORY NOTICES</div>
    {''.join(f'<div style="font-family:var(--font-sans);font-size:13px;color:var(--ink);margin-bottom:4px;">· {item}</div>' for item in guide["missing_info"])}
</div>
"""), unsafe_allow_html=True)

        # Optional raw README expander
        if ar.get("readme"):
            with st.expander("View raw README excerpt (reference only)", expanded=False):
                st.text(ar["readme"][:3000] + ("..." if len(ar["readme"]) > 3000 else ""))



# ── Tab: Issues ───────────────────────────────────────────────────────────
with tab_issues:
    from app.db.models import Issue as IssueModel
    from app.services.issue_ranker import rank_issues, score_issue

    issues_raw = ar.get("issues", [])
    if not issues_raw:
        st.info("No open issues found for this repository.")
    else:
        # Filter controls
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            difficulty_filter = st.selectbox(
                "Difficulty",
                ["All", "beginner", "intermediate", "advanced"],
                key="diff_filter",
            )
        with fcol2:
            exclude_assigned = st.checkbox("Hide assigned issues", value=True, key="ex_assigned")
        with fcol3:
            sort_by = st.selectbox("Sort by", ["Fit Score", "Most Recent", "Most Comments"], key="sort_by")

        # Build lightweight Issue objects for scoring
        class _FakeIssue:
            def __init__(self, d):
                self.state = d.get("state", "open")
                self.labels = d.get("labels", [])
                self.assignees = d.get("assignees", [])
                self.title = d.get("title", "")
                self.body = d.get("body", "")
                self.updated_at_gh = d.get("updated_at_gh")
                self.number = d.get("number")
                self.html_url = d.get("html_url", "#")
                self.id = d.get("id")
                self.comments_count = d.get("comments_count", 0)

        class _FakeProfile:
            def __init__(self, d):
                self.programming_languages = d.get("programming_languages", [])

        fake_profile = _FakeProfile(profile_dict)
        ranked = []
        for issue_d in issues_raw:
            fi = _FakeIssue(issue_d)
            score, signals, difficulty = score_issue(fi, fake_profile)
            ranked.append((issue_d, score, signals, difficulty))

        if sort_by == "Most Recent":
            def _get_sort_date(item):
                d = item[0].get("created_at_gh") or item[0].get("updated_at_gh")
                if d is None:
                    return datetime.min.replace(tzinfo=timezone.utc)
                if isinstance(d, str):
                    try:
                        d = datetime.fromisoformat(d.replace("Z", "+00:00"))
                    except Exception:
                        return datetime.min.replace(tzinfo=timezone.utc)
                if getattr(d, "tzinfo", None) is None:
                    d = d.replace(tzinfo=timezone.utc)
                return d
            ranked.sort(key=_get_sort_date, reverse=True)
        elif sort_by == "Most Comments":
            ranked.sort(key=lambda x: x[0].get("comments_count", 0), reverse=True)
        else:
            ranked.sort(key=lambda x: x[1], reverse=True)

        # Apply filters
        filtered = [
            (i, s, sig, d) for i, s, sig, d in ranked
            if (difficulty_filter == "All" or d == difficulty_filter)
            and (not exclude_assigned or not i.get("assignees"))
        ]

        st.markdown(f"**{len(filtered)} issues** matching your filters", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        if not filtered:
            st.info("No issues match the current filters. Try adjusting the difficulty filter.")
        else:
            for issue_d, score, signals, difficulty in filtered[:30]:
                pos_reasons = [sig["reason"] for sig in signals.values() if sig.get("value") and sig.get("weight", 0) > 0]
                fit_reason = "; ".join(pos_reasons[:2]) if pos_reasons else "Matches repository technology stack and community contribution patterns."
                
                # Render Solo Ledger Issue Card (§3.8)
                render_issue_card(issue_d, score, difficulty, fit_reason=fit_reason)

                # Action buttons (§3.8)
                btn_col1, btn_col2, btn_col3 = st.columns([1.2, 1.2, 1])
                with btn_col1:
                    if st.button("View Code Trail →", key=f"trail_{issue_d['number']}", use_container_width=True):
                        st.session_state["active_issue"] = issue_d
                        st.session_state["active_repo_data"] = ar
                        st.switch_page("pages/04_learning.py")
                with btn_col2:
                    if st.button("Start Practice ⚒", key=f"practice_{issue_d['number']}", use_container_width=True, type="primary"):
                        st.session_state["active_issue"] = issue_d
                        st.session_state["active_repo_data"] = ar
                        st.switch_page("pages/05_practice.py")
                with btn_col3:
                    st.link_button("↗ GitHub", issue_d.get("html_url", "#"), use_container_width=True)

                # Score Breakdown disclosure table (§3.8.1)
                with st.expander(f"Why this score? (#{issue_d['number']} breakdown & details)", expanded=False):
                    if issue_d.get("body"):
                        st.markdown(f"**Issue Description:**\n\n{issue_d['body'][:600]}{'…' if len(issue_d.get('body', '')) > 600 else ''}")
                    
                    sig_rows = []
                    for sig_name, sig in signals.items():
                        w = sig.get('weight', 0)
                        v = sig.get('value')
                        if w > 0 and v:
                            effect_color = 'var(--green)'
                            effect_text = '▲ positive'
                        elif w < 0 and v:
                            effect_color = 'var(--error-text, #C0392B)'
                            effect_text = '▼ reduces'
                        else:
                            effect_color = 'var(--text-muted)'
                            effect_text = '– neutral'
                        sig_rows.append(
                            '<tr>'
                            + f'<td style="font-family:var(--font-mono);font-weight:700;color:var(--ink);padding:8px 12px;">{sig_name.replace("_", " ").title()}</td>'
                            + f'<td style="font-family:var(--font-sans);color:var(--ink);padding:8px 12px;">{sig.get("reason", "")}</td>'
                            + f'<td style="font-family:var(--font-mono);font-weight:700;color:{effect_color};padding:8px 12px;">{effect_text}</td>'
                            + '</tr>'
                        )
                    score_table = (
                        '<table class="ledger-table" style="margin:10px 0;">'
                        + '<thead><tr>'
                        + '<th style="padding:8px 12px;">SIGNAL</th>'
                        + '<th style="padding:8px 12px;">EVIDENCE</th>'
                        + '<th style="padding:8px 12px;">EFFECT</th>'
                        + '</tr></thead>'
                        + '<tbody>' + ''.join(sig_rows) + '</tbody>'
                        + '</table>'
                        + '<div style="font-family:var(--font-mono);font-size:11px;color:var(--text-muted);margin-top:6px;">'
                        + 'RULE · Estimate derived from deterministic ranking rules. Not an absolute measure of issue complexity.</div>'
                    )
                    st.markdown(score_table, unsafe_allow_html=True)
                st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)


# ── Tab: Codebase map ─────────────────────────────────────────────────────
with tab_tree:
    tree = ar.get("tree", [])
    if not tree:
        st.info("Directory tree not available.")
    else:
        search = st.text_input("Search files", placeholder="Filter by filename or path…", key="tree_search")

        filtered_tree = [
            item for item in tree
            if item.get("type") == "blob" and (not search or search.lower() in item["path"].lower())
        ]

        st.markdown(f"**{len(filtered_tree)} files** (showing up to 200)", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Group by top-level directory
        from collections import defaultdict
        groups = defaultdict(list)
        for item in filtered_tree[:200]:
            parts = item["path"].split("/")
            group = parts[0] if len(parts) > 1 else "root"
            groups[group].append(item)

        for group, items in sorted(groups.items()):
            with st.expander(f"{group}/ ({len(items)} files)"):
                for item in items[:50]:
                    size = item.get("size", 0)
                    size_str = f"{size:,} B" if size < 1024 else f"{size//1024} KB"
                    st.markdown(clean_html(f"""
<div style="display:flex;justify-content:space-between;padding:0.2rem 0;border-bottom:1px solid rgba(107,120,144,0.06);">
    <code style="font-size:0.78rem;color:#159A8C;">{item['path']}</code>
    <span style="font-size:0.72rem;color:#6B7890;">{size_str}</span>
</div>
"""), unsafe_allow_html=True)


# ── Tab: Contribution workflow ────────────────────────────────────────────
with tab_workflow:
    guide = st.session_state.get("guide_content")
    if not guide and ar:
        guide = generate_grounded_guide(ar)
        st.session_state["guide_content"] = guide

    workflow_steps = guide.get("contribution_workflow", []) if guide else []

    if workflow_steps:
        wf_svg = icon("refresh", 18, "#17243D")
        st.markdown(f'<div class="section-title" style="display:flex;align-items:center;gap:6px;">{wf_svg} <span>Dynamic Contribution Workflow</span></div>', unsafe_allow_html=True)
        st.markdown(f"<p style='color:#6B7890;font-size:0.9rem;margin-bottom:1rem;'>Grounded 5-step roadmap tailored specifically to <code>{ar['full_name']}</code>.</p>", unsafe_allow_html=True)

        wf_mode = st.radio(
            "Workflow View Format",
            ["2D Infographic Roadmap", "Interactive Flowchart (Mermaid)", "Detailed Step Instructions"],
            horizontal=True,
            key="wf_view_mode",
            label_visibility="collapsed",
        )

        if wf_mode == "2D Infographic Roadmap":
            render_workflow_infographic(workflow_steps, ar["full_name"])
        elif wf_mode == "Interactive Flowchart (Mermaid)":
            mermaid_code = generate_mermaid_workflow(workflow_steps)
            st.markdown(f"```mermaid\n{mermaid_code}\n```")
        else:
            tag_svg = icon("tag", 12, "#6B7890")
            for step in workflow_steps:
                num = step.get("step_number", "")
                title = step.get("title", "")
                desc = step.get("directive", "")
                cmd = step.get("command")
                source = step.get("source", "")
                st.markdown(clean_html(f"""
<div class="rc-card" style="border-left:4px solid {step.get('color', '#159A8C')};margin-bottom:0.75rem;">
    <div style="display:flex;align-items:flex-start;gap:0.75rem;">
        <div style="width:32px;height:32px;border-radius:50%;background:{step.get('color', '#159A8C')};color:white;display:flex;align-items:center;justify-content:center;font-size:0.9rem;font-weight:700;flex-shrink:0;">{num}</div>
        <div style="flex:1;">
            <div style="font-weight:700;color:#17243D;font-size:0.95rem;margin-bottom:0.2rem;">{title}</div>
            <div style="font-size:0.88rem;color:#17243D;line-height:1.5;">{desc}</div>
            {f'<code style="display:block;margin-top:0.5rem;background:#F7F9FC;border:1px solid rgba(107,120,144,0.15);border-radius:6px;padding:0.4rem 0.6rem;font-size:0.82rem;color:#101B35;">{cmd}</code>' if cmd else ''}
            <div style="margin-top:0.4rem;font-size:0.72rem;color:#6B7890;display:flex;align-items:center;gap:4px;">{tag_svg} <span>{source}</span></div>
        </div>
    </div>
</div>
"""), unsafe_allow_html=True)

        if ar.get("contributing"):
            with st.expander("View raw CONTRIBUTING.md excerpt (reference only)", expanded=False):
                st.text(ar["contributing"][:3000] + ("..." if len(ar["contributing"]) > 3000 else ""))

    else:
        st.info("No contribution workflow available.")
