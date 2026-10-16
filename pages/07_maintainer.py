"""
Maintainer Studio — issue quality checks, classification (including needs-more-information),
draft improvements, starter issues, and post-merge related issue discovery.
All generated content remains a draft until approved. No automatic writes to GitHub.
"""
import streamlit as st

st.set_page_config(
    page_title="RepoCompass — Maintainer Studio",
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
    render_top_status_bar, render_page_header,
    render_mini_stat_card, render_status_pill, render_ai_block,
)
from app.ui.icons import icon
from app.services.llm_service import (
    generate_json, SYSTEM_PROMPT, check_ollama_available,
    LLMUnavailableError, LLMOutputError,
)
from app.services.issue_ranker import score_issue
from app.services.maintainer_service import (
    analyze_issue_quality,
    classify_issue_maintainer,
    generate_grounded_improvement_draft,
    generate_grounded_starter_draft,
    find_related_issues_for_pr,
)
from app.db.session import get_db
from app.db.models import MaintainerDraft
import uuid
from datetime import datetime, timezone

inject_global_css()
render_top_status_bar(is_live=True)
render_sidebar_nav("maintainer")

user = require_auth()
if not user:
    st.stop()

user_id = user["id"]
ollama_ok = check_ollama_available()

# ─── Page Title Header (§3.3) ──────────────────────────────────────────────

render_page_header(
    "Maintainer Studio",
    "Issue Triage & Quality Governance",
    caption="Issue Quality Scoring · Needs-More-Info Classification · Grounded Starter Drafts · Post-Merge Discovery"
)

st.markdown(clean_html("""
<div class="rc-card card--tan" style="padding:12px 16px;margin-bottom:1.5rem;">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
        <span class="pill pill-amber">⚠ HUMAN-IN-THE-LOOP</span>
        <span style="font-family:var(--font-sans);font-weight:700;font-size:13px;color:var(--ink);">Draft Policy Guardrail</span>
    </div>
    <div style="font-family:var(--font-sans);font-size:12px;color:var(--ink);line-height:1.4;">
        All improvements, starter issue scaffolds, and comment templates are saved strictly as <strong>local drafts</strong>. 
        Zero automated write calls are made to GitHub without maintainer review and explicit confirmation.
    </div>
</div>
"""), unsafe_allow_html=True)

repo_data = st.session_state.get("analysis_result")
if not repo_data:
    st.info("Analyze a repository in **Explore Repositories** to activate Maintainer Studio.")
    if st.button("Go to Explore", type="primary"):
        st.switch_page("pages/03_explore.py")
    st.stop()

issues = repo_data.get("issues", [])
if not issues:
    st.info("No open issues found in the analyzed repository.")
    st.stop()

# ─── Compute Triage and Quality Metrics ───────────────────────────────────

class _FakeIssue:
    def __init__(self, d):
        self.state = d.get("state", "open")
        self.labels = d.get("labels", [])
        self.assignees = d.get("assignees", [])
        self.title = d.get("title", "")
        self.body = d.get("body", "")
        self.updated_at_gh = d.get("updated_at_gh")

triage_list = []
quality_passed_repro = 0
needs_info_count = 0
beginner_candidates = 0

for issue_d in issues:
    fi = _FakeIssue(issue_d)
    score, signals, base_diff = score_issue(fi)
    q_data = analyze_issue_quality(issue_d)
    final_diff = classify_issue_maintainer(issue_d, base_diff)

    if q_data["checks"]["has_repro_steps"]:
        quality_passed_repro += 1
    if final_diff == "needs-more-information":
        needs_info_count += 1
    if final_diff == "beginner":
        beginner_candidates += 1

    triage_list.append({
        "issue": issue_d,
        "score": score,
        "signals": signals,
        "difficulty": final_diff,
        "quality": q_data,
    })

triage_list.sort(key=lambda x: x["score"], reverse=True)

# ─── Repository Quality Health Overview (§3.6.3) ───────────────────────────

repro_pct = int(quality_passed_repro / max(len(issues), 1) * 100)
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    render_mini_stat_card("TOTAL ANALYZED", f"{len(issues)}", "Issues in repository manifest")
with col_m2:
    render_mini_stat_card("WITH REPRO STEPS", f"{repro_pct}%", f"{quality_passed_repro} issues passed checklist")
with col_m3:
    render_mini_stat_card("NEEDS MORE INFO", f"{needs_info_count}", "Missing reproduction or stack trace")
with col_m4:
    render_mini_stat_card("STARTER CANDIDATES", f"{beginner_candidates}", "Good for community newcomers")

st.markdown("<div style='margin-bottom:1.5rem;'></div>", unsafe_allow_html=True)

# ─── Studio Tabs ──────────────────────────────────────────────────────────

tab_triage, tab_postmerge, tab_approved = st.tabs([
    "Issue Triage & Drafts",
    "Post-Merge Related Issues",
    "Saved Approved Drafts",
])


# ── Tab 1: Issue Triage ───────────────────────────────────────────────────
with tab_triage:
    f_col1, f_col2 = st.columns([1, 1])
    with f_col1:
        diff_filter = st.selectbox(
            "Filter by Classification",
            ["All", "needs-more-information", "beginner", "intermediate", "advanced"],
            key="mt_diff_filter",
        )
    with f_col2:
        hide_assigned = st.checkbox("Show only unassigned issues", value=True, key="mt_unassigned_chk")

    filtered = [
        item for item in triage_list
        if (diff_filter == "All" or item["difficulty"] == diff_filter)
        and (not hide_assigned or item["quality"]["checks"]["is_unassigned"])
    ]

    st.markdown(f"**Showing {len(filtered)} matching issues:**")
    st.markdown("<br>", unsafe_allow_html=True)

    diff_badge_colors = {
        "beginner": "#21866D",
        "intermediate": "#C8872D",
        "advanced": "#C94C4C",
        "needs-more-information": "#7565C7",
    }

    for item in filtered[:25]:
        issue_d = item["issue"]
        num = issue_d["number"]
        difficulty = item["difficulty"]
        q_data = item["quality"]
        score = item["score"]

        color = diff_badge_colors.get(difficulty, "#6B7890")

        with st.expander(f"#{num} — {issue_d['title'][:70]} | [{difficulty.upper()}] | Quality: {q_data['quality_score']}%"):
            c_left, c_right = st.columns([2.5, 1.2])

            with c_left:
                st.markdown(f"**[#{num}: {issue_d['title']}]({issue_d['html_url']})**")
                body_prev = (issue_d.get("body") or "No description provided.")[:400]
                st.markdown(f"<p style='font-size:0.84rem;color:#6B7890;line-height:1.5;'>{body_prev}...</p>", unsafe_allow_html=True)

                st.markdown("**Specification Quality Checklist:**")
                checks = q_data["checks"]
                chk_y = icon("check", 13, "#21866D")
                chk_w = icon("alert_triangle", 13, "#C8872D")
                chk_i = icon("info", 13, "#6B7890")
                q_col1, q_col2 = st.columns(2)
                with q_col1:
                    st.markdown(f"<div style='display:flex;align-items:center;gap:4px;margin:2px 0;'>{chk_y if checks['has_description'] else chk_w} <span>Problem Description</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='display:flex;align-items:center;gap:4px;margin:2px 0;'>{chk_y if checks['has_repro_steps'] else chk_w} <span>Reproduction Steps</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='display:flex;align-items:center;gap:4px;margin:2px 0;'>{chk_y if checks['has_expected_vs_actual'] else chk_w} <span>Expected vs Actual</span></div>", unsafe_allow_html=True)
                with q_col2:
                    st.markdown(f"<div style='display:flex;align-items:center;gap:4px;margin:2px 0;'>{chk_y if checks['has_logs_or_code'] else chk_w} <span>Error Logs / Code</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='display:flex;align-items:center;gap:4px;margin:2px 0;'>{chk_y if checks['has_acceptance_criteria'] else chk_w} <span>Acceptance Criteria</span></div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='display:flex;align-items:center;gap:4px;margin:2px 0;'>{chk_y if checks['is_unassigned'] else chk_i} <span>Unassigned Status</span></div>", unsafe_allow_html=True)

                if q_data["missing_items"]:
                    st.markdown(f"<div style='font-size:0.75rem;color:#C8872D;margin-top:0.4rem;display:flex;align-items:center;gap:4px;'>{chk_w} <span>Missing context: {', '.join(q_data['missing_items'])}</span></div>", unsafe_allow_html=True)

            with c_right:
                st.markdown(clean_html(f"""
<div style="text-align:center;padding:1rem;background:#F8FAFC;border:1px solid rgba(107,120,144,0.15);border-radius:10px;">
    <div style="font-size:1.1rem;font-weight:700;color:{color};">{difficulty.upper()}</div>
    <div style="font-size:0.7rem;color:#6B7890;margin-bottom:0.6rem;">Classification</div>
    <div style="font-size:1.6rem;font-weight:800;color:#159A8C;">{q_data['quality_score']}%</div>
    <div style="font-size:0.7rem;color:#6B7890;">Completeness Score</div>
</div>
"""), unsafe_allow_html=True)
                if issue_d.get("labels"):
                    st.markdown("<div style='margin-top:0.5rem;'><strong>Labels:</strong> " + " ".join(f"`{l}`" for l in issue_d["labels"][:4]) + "</div>", unsafe_allow_html=True)

            # Actions
            st.markdown("<hr style='margin:0.75rem 0;'>", unsafe_allow_html=True)
            act1, act2, act3 = st.columns([1.2, 1.2, 0.8])

            with act1:
                if st.button("Draft Improvement", key=f"btn_imp_{num}", use_container_width=True):
                    # Check Ollama or generate grounded draft
                    draft = generate_grounded_improvement_draft(issue_d, q_data)
                    if ollama_ok:
                        prompt = f"""You are RepoCompass AI helping a maintainer clarify this GitHub issue.
Issue #{num}: {issue_d['title']}
Body: {(issue_d.get('body') or '')[:800]}
Missing: {q_data['missing_items']}

Return JSON:
{{
  "improved_title": "{draft['improved_title']}",
  "improved_body": "Detailed clarified markdown body with steps to reproduce and acceptance criteria",
  "rationale": "Why these changes improve contributor clarity"
}}"""
                        try:
                            ai_draft = generate_json(prompt, system=SYSTEM_PROMPT, schema_keys=["improved_body"])
                            if ai_draft.get("improved_body"):
                                draft["improved_body"] = ai_draft["improved_body"]
                                draft["improved_title"] = ai_draft.get("improved_title", draft["improved_title"])
                                draft["rationale"] = ai_draft.get("rationale", draft["rationale"])
                                draft["source"] = "ai_enriched"
                        except Exception:
                            pass

                    st.session_state[f"active_draft_{num}"] = draft
                    st.rerun()

            with act2:
                if st.button("Draft Starter Task", key=f"btn_start_{num}", use_container_width=True):
                    starter = generate_grounded_starter_draft(issue_d)
                    if ollama_ok:
                        prompt = f"""Create a scoped good first issue starter task derived from issue #{num}: {issue_d['title']}
Body: {(issue_d.get('body') or '')[:600]}
Return JSON:
{{
  "starter_title": "{starter['starter_title']}",
  "starter_body": "Clear step-by-step beginner task body with test requirement",
  "scope_explanation": "Why this is safe and small for a beginner"
}}"""
                        try:
                            ai_starter = generate_json(prompt, system=SYSTEM_PROMPT, schema_keys=["starter_body"])
                            if ai_starter.get("starter_body"):
                                starter["starter_body"] = ai_starter["starter_body"]
                                starter["starter_title"] = ai_starter.get("starter_title", starter["starter_title"])
                                starter["scope_explanation"] = ai_starter.get("scope_explanation", starter["scope_explanation"])
                                starter["source"] = "ai_enriched"
                        except Exception:
                            pass

                    st.session_state[f"active_starter_{num}"] = starter
                    st.rerun()

            with act3:
                st.link_button("GitHub ↗", issue_d["html_url"], use_container_width=True)

            # Display Draft Improvement Review & Edit Area
            active_draft = st.session_state.get(f"active_draft_{num}")
            if active_draft:
                edit_svg = icon("edit", 16, "#17243D")
                st.markdown(f'<div class="section-title" style="display:flex;align-items:center;gap:6px;">{edit_svg} <span>Review & Edit Issue Improvement</span></div>', unsafe_allow_html=True)
                edited_title = st.text_input("Title", value=active_draft.get("improved_title", ""), key=f"et_{num}")
                edited_body = st.text_area("Body (Markdown)", value=active_draft.get("improved_body", ""), height=220, key=f"eb_{num}")

                b_save, b_copy, b_discard = st.columns([1, 1, 1])
                with b_save:
                    if st.button("Approve & Save Draft", key=f"save_drf_{num}", use_container_width=True):
                        try:
                            with get_db() as session:
                                md = MaintainerDraft(
                                    id=str(uuid.uuid4()),
                                    user_id=user_id,
                                    repository_id=repo_data.get("repo_id") or str(uuid.uuid4()),
                                    issue_id=str(issue_d.get("id")),
                                    draft_type="improvement",
                                    title=edited_title,
                                    content=edited_body,
                                    rationale=active_draft.get("rationale", ""),
                                    status="approved",
                                )
                                session.add(md)
                            st.success("Draft approved and saved to your repository records!")
                        except Exception as e:
                            st.error(f"Save error: {e}")

                with b_copy:
                    if st.button("Copy Markdown", key=f"cpy_drf_{num}", use_container_width=True):
                        st.code(edited_body)

                with b_discard:
                    if st.button("Discard Draft", key=f"dsc_drf_{num}", use_container_width=True):
                        st.session_state.pop(f"active_draft_{num}", None)
                        st.rerun()

            # Display Starter Issue Review & Edit Area
            active_starter = st.session_state.get(f"active_starter_{num}")
            if active_starter:
                spk_svg = icon("sparkles", 16, "#159A8C")
                st.markdown(f'<div class="section-title" style="display:flex;align-items:center;gap:6px;">{spk_svg} <span>Review & Edit Starter Issue</span></div>', unsafe_allow_html=True)
                st_title = st.text_input("Starter Title", value=active_starter.get("starter_title", ""), key=f"st_t_{num}")
                st_body = st.text_area("Starter Task Body", value=active_starter.get("starter_body", ""), height=220, key=f"st_b_{num}")

                s_save, s_copy, s_discard = st.columns([1, 1, 1])
                with s_save:
                    if st.button("Approve Starter Issue", key=f"save_str_{num}", use_container_width=True):
                        try:
                            with get_db() as session:
                                md = MaintainerDraft(
                                    id=str(uuid.uuid4()),
                                    user_id=user_id,
                                    repository_id=repo_data.get("repo_id") or str(uuid.uuid4()),
                                    issue_id=str(issue_d.get("id")),
                                    draft_type="starter_issue",
                                    title=st_title,
                                    content=st_body,
                                    rationale=active_starter.get("scope_explanation", ""),
                                    status="approved",
                                )
                                session.add(md)
                            st.success("Starter issue approved and saved!")
                        except Exception as e:
                            st.error(f"Save error: {e}")

                with s_copy:
                    if st.button("Copy Markdown", key=f"cpy_str_{num}", use_container_width=True):
                        st.code(st_body)

                with s_discard:
                    if st.button("Discard", key=f"dsc_str_{num}", use_container_width=True):
                        st.session_state.pop(f"active_starter_{num}", None)
                        st.rerun()


# ── Tab 2: Post-Merge Related Issues ──────────────────────────────────────
with tab_postmerge:
    link_svg = icon("link", 18, "#17243D")
    st.markdown(f'<div class="section-title" style="display:flex;align-items:center;gap:6px;">{link_svg} <span>Post-Merge Related Open Issues Finder</span></div>', unsafe_allow_html=True)
    st.markdown(clean_html("""
<div style="font-size:0.85rem;color:#6B7890;margin-bottom:1rem;">
    When a Pull Request is merged, enter the files modified in that PR to discover other open issues
    that touch the same modules or symbols. Helps prevent duplicate work and keeps issues aligned.
</div>
"""), unsafe_allow_html=True)

    c_files_input = st.text_area(
        "Enter modified file paths (one per line):",
        placeholder="fastapi/routing.py\ntests/test_routing.py",
        height=100,
        key="pm_files_input",
    )

    if st.button("Find Related Open Issues", type="primary", key="find_rel_btn"):
        changed_paths = [f.strip() for f in c_files_input.splitlines() if f.strip()]
        if not changed_paths:
            st.warning("Please enter at least one modified file path.")
        else:
            related_results = find_related_issues_for_pr(
                changed_files=changed_paths,
                all_issues=issues,
            )
            st.session_state["related_results"] = related_results

    rel_res = st.session_state.get("related_results")
    if rel_res is not None:
        if not rel_res:
            st.info("No open issues directly overlap with the specified files.")
        else:
            st.markdown(f"**Found {len(rel_res)} open issue(s) related to these changes:**")
            for rel in rel_res:
                st.markdown(clean_html(f"""
<div class="rc-card" style="margin-bottom:0.6rem;border-left:4px solid #159A8C;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div>
            <div style="font-weight:700;font-size:0.92rem;color:#17243D;">
                <a href="{rel['html_url']}" target="_blank" style="color:#101B35;text-decoration:none;">#{rel['number']}: {rel['title']} ↗</a>
            </div>
            <div style="font-size:0.78rem;color:#6B7890;margin-top:0.25rem;">
                {' · '.join(rel['reasons'])}
            </div>
        </div>
        <span class="badge badge-teal" style="font-size:0.7rem;">Match Score: {rel['score']:.0f}</span>
    </div>
</div>
"""), unsafe_allow_html=True)


# ── Tab 3: Saved Approved Drafts ──────────────────────────────────────────
with tab_approved:
    folder_svg = icon("folder", 18, "#17243D")
    st.markdown(f'<div class="section-title" style="display:flex;align-items:center;gap:6px;">{folder_svg} <span>Approved Repository Drafts</span></div>', unsafe_allow_html=True)


    try:
        with get_db() as session:
            repo_id = repo_data.get("repo_id")
            saved_drafts = (
                session.query(MaintainerDraft)
                .filter_by(user_id=user_id)
                .order_by(MaintainerDraft.created_at.desc())
                .all()
            )
            draft_records = [
                {
                    "id": d.id,
                    "title": d.title,
                    "content": d.content,
                    "draft_type": d.draft_type,
                    "status": d.status,
                    "created_at": d.created_at,
                }
                for d in saved_drafts
            ]
    except Exception as e:
        draft_records = []

    if not draft_records:
        st.info("No approved drafts saved yet. Review issues in the Triage tab and click 'Approve & Save Draft'.")
    else:
        st.markdown(f"**{len(draft_records)} approved draft(s) on record:**")
        for dr in draft_records:
            st.markdown(clean_html(f"""
<div class="rc-card" style="margin-bottom:0.75rem;">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.4rem;">
        <span class="badge badge-teal">{dr['draft_type'].upper()}</span>
        <span style="font-size:0.75rem;color:#6B7890;">Saved: {dr['created_at'].strftime('%Y-%m-%d %H:%M') if dr['created_at'] else 'recent'}</span>
    </div>
    <div style="font-weight:700;color:#101B35;font-size:0.95rem;margin-bottom:0.4rem;">{dr['title']}</div>
    <div style="font-size:0.82rem;color:#6B7890;white-space:pre-wrap;max-height:160px;overflow-y:auto;background:#F8FAFC;padding:0.6rem;border-radius:6px;border:1px solid rgba(107,120,144,0.1);">{dr['content']}</div>
</div>
"""), unsafe_allow_html=True)
