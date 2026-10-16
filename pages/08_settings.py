"""
Settings — profile, skill preferences, privacy, model status, data.
"""
import streamlit as st

st.set_page_config(
    page_title="RepoCompass — Settings",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys
for mod in list(sys.modules.keys()):
    if mod.startswith("app."):
        del sys.modules[mod]

import json
from app.ui.shared import (
    clean_html,
    inject_global_css, require_auth, render_sidebar_nav,
    render_top_status_bar, render_page_header, render_status_pill,
    set_current_user, clear_current_user,
)
from app.ui.icons import icon
from app.db.session import get_db, get_db_info
from app.db.models import User, Profile
from app.services.llm_service import (
    check_ollama_available, list_available_models, last_llm_stats, reset_ollama_cache,
)
from app.core.config import get_settings
from app.core.supabase import is_supabase_online
from app.services.ml_survey_service import ML_QUESTIONS, get_user_ml_survey, save_user_ml_survey

inject_global_css()
render_top_status_bar(is_live=True)
render_sidebar_nav("settings")

user = require_auth()
if not user:
    st.stop()

user_id = user["id"]
settings = get_settings()

# ─── Load user & profile safely inside session to prevent DetachedInstanceError ─
with get_db() as session:
    user_obj = session.query(User).filter_by(id=user_id).first()
    profile_obj = session.query(Profile).filter_by(user_id=user_id).first()

    user_email = user_obj.email if user_obj else user.get("email", "")
    user_created = user_obj.created_at.strftime('%B %Y') if (user_obj and user_obj.created_at) else "—"
    user_display_name = user_obj.display_name if user_obj else user.get("display_name", "")

    bio_val = profile_obj.bio or "" if profile_obj else ""
    current_exp = profile_obj.experience_level if (profile_obj and profile_obj.experience_level) else "beginner"
    languages_val = list(profile_obj.programming_languages) if (profile_obj and profile_obj.programming_languages) else []
    interests_val = list(profile_obj.interests) if (profile_obj and profile_obj.interests) else []
    comfortable_git_val = bool(profile_obj.comfortable_with_git) if profile_obj else True
    comfortable_testing_val = bool(profile_obj.comfortable_with_testing) if profile_obj else False
    leaderboard_visible_val = bool(profile_obj.leaderboard_visible) if profile_obj else False
    profile_public_val = bool(profile_obj.profile_public) if profile_obj else True

# ─── Page Title Header (§3.3) ──────────────────────────────────────────────

render_page_header(
    "Settings",
    "Preferences & System Health",
    caption="Profile Configuration · 8-Question ML Feature Survey · Privacy Controls · AI & Cloud Service Diagnostics"
)

tab_profile, tab_ml, tab_privacy, tab_model, tab_data = st.tabs([
    "Profile & Session", "ML Model Survey", "Privacy", "AI & Cloud Status", "Data"
])


# ─── Profile tab ──────────────────────────────────────────────────────────

with tab_profile:
    st.markdown("#### Account details")
    st.markdown(f"**Email:** {user_email}")
    st.markdown(f"**Member since:** {user_created}")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Edit profile")

    with st.form("profile_form"):
        new_name = st.text_input("Display name", value=user_display_name)
        bio = st.text_area("Bio (optional)", value=bio_val, max_chars=200)

        exp_options = ["beginner", "intermediate", "advanced"]
        exp_idx = exp_options.index(current_exp) if current_exp in exp_options else 0
        new_exp = st.selectbox("Experience level", exp_options, index=exp_idx)

        languages = st.multiselect(
            "Programming languages",
            options=[
                "Python", "JavaScript", "TypeScript", "Java", "C", "C++", "C#",
                "Go", "Rust", "Ruby", "PHP", "Swift", "Kotlin", "Shell/Bash",
                "SQL", "HTML/CSS", "R", "Scala", "Dart", "Lua",
            ],
            default=languages_val,
        )

        interests = st.multiselect(
            "Interests",
            options=[
                "Web development", "API / backend", "Machine learning / AI",
                "DevOps / infrastructure", "Data engineering", "Mobile",
                "Documentation", "Testing / QA", "Security", "Open-source tooling",
            ],
            default=interests_val,
        )

        comfortable_git = st.checkbox("Comfortable with Git", value=comfortable_git_val)
        comfortable_testing = st.checkbox("Comfortable with testing", value=comfortable_testing_val)

        save_profile = st.form_submit_button("Save Changes", type="primary")

    if save_profile:
        try:
            with get_db() as s:
                u = s.query(User).filter_by(id=user_id).first()
                p = s.query(Profile).filter_by(user_id=user_id).first()
                if u:
                    u.display_name = new_name.strip()
                if p:
                    p.bio = bio.strip()
                    p.experience_level = new_exp
                    p.programming_languages = languages
                    p.interests = interests
                    p.comfortable_with_git = comfortable_git
                    p.comfortable_with_testing = comfortable_testing

            # Update session
            set_current_user({**user, "display_name": new_name.strip()})
            st.success("Profile saved!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save: {e}")

    st.markdown("---")
    st.markdown("#### Account Session & Security")
    st.markdown("<p style='font-size:0.88rem;color:#6B7890;'>Need to end your session or switch accounts?</p>", unsafe_allow_html=True)
    col_so, _ = st.columns([1.2, 3])
    with col_so:
        if st.button("🚪 Sign Out of RepoCompass", key="profile_sign_out_btn", type="secondary", use_container_width=True):
            clear_current_user()
            st.success("Signed out successfully.")
            st.switch_page("pages/01_auth.py")


# ─── ML Survey & Model Calibration tab ─────────────────────────────────────

with tab_ml:
    st.markdown("#### ML Issue Recommendation Calibration")
    st.markdown(clean_html("""
<div style="background:rgba(21,154,140,0.06);border:1px solid rgba(21,154,140,0.2);border-radius:10px;padding:1rem;margin-bottom:1.5rem;">
    <div style="font-weight:600;color:#159A8C;margin-bottom:0.25rem;">8-Question Background & Skill Profile for ML Matching</div>
    <div style="font-size:0.85rem;color:#4B5563;line-height:1.5;">
        These questions calibrate your coding background, past Git operations, time commitment, and preferred issue types.
        When our issue recommendation ML model is trained, it uses this normalized feature vector to surface high-signal first issues tailored specifically to you.
    </div>
</div>
"""), unsafe_allow_html=True)

    ml_data = get_user_ml_survey(user_id) or {}
    saved_survey = ml_data.get("survey") or {}
    saved_features = ml_data.get("features") or {}

    # Display current calibrated vector metrics if present
    if saved_features:
        st.markdown("##### Current ML Calibrated Vector")
        mcol1, mcol2, mcol3, mcol4 = st.columns(4)
        mcol1.metric("Experience Tier", saved_features.get("calibrated_tier", "beginner").upper())
        mcol2.metric("OSS Actions Score", f"{saved_features.get('oss_experience_score', 0):.2f}")
        mcol3.metric("Git Competency", f"{saved_features.get('git_skill_score', 0):.2f}")
        mcol4.metric("Weekly Hours", f"{saved_features.get('weekly_hours_available', 0)} hrs")

        export_payload = {
            "user_id": user_id,
            "raw_survey": saved_survey,
            "feature_vector": saved_features,
            "exported_at": str(user_created)
        }
        json_str = json.dumps(export_payload, indent=2)
        st.download_button(
            label="📥 Download ML Training Sample (JSON)",
            data=json_str,
            file_name=f"ml_contributor_profile_{user_id[:8]}.json",
            mime="application/json",
            help="Export this feature vector for training your issue ranking ML model."
        )
        st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("##### Update Questionnaire Answers")
    with st.form("ml_survey_settings_form"):
        updated_answers = {}
        for q in ML_QUESTIONS:
            qid = q["id"]
            num = q["number"]
            title = q["title"]
            subtitle = q.get("subtitle", "")
            qtype = q["type"]
            options = q["options"]
            default_val = saved_survey.get(qid, q.get("default"))

            st.markdown(f"**Q{num}. {title}**")
            if subtitle:
                st.caption(subtitle)

            if qtype == "multiselect":
                if not isinstance(default_val, list):
                    default_val = [default_val] if default_val else []
                valid_defaults = [o for o in default_val if o in options]
                updated_answers[qid] = st.multiselect(
                    label=title,
                    options=options,
                    default=valid_defaults,
                    key=f"sett_ml_{qid}",
                    label_visibility="collapsed"
                )
            elif qtype == "radio":
                default_idx = options.index(default_val) if default_val in options else 0
                updated_answers[qid] = st.radio(
                    label=title,
                    options=options,
                    index=default_idx,
                    key=f"sett_ml_{qid}",
                    label_visibility="collapsed"
                )
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        save_ml = st.form_submit_button("Save & Recalibrate ML Features", type="primary")

    if save_ml:
        try:
            new_feats = save_user_ml_survey(user_id, updated_answers)
            st.success(f"ML Profile saved! Calibrated tier: {new_feats.get('calibrated_tier', 'beginner').upper()}")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to update ML survey: {e}")


# ─── Privacy tab ──────────────────────────────────────────────────────────

with tab_privacy:
    st.markdown("#### Leaderboard visibility")
    st.markdown(clean_html("""
<div class="alert-info">
    Leaderboard participation is opt-in. Your name and XP are only visible to others 
    if you enable this. You can disable it at any time.
</div>
"""), unsafe_allow_html=True)

    with st.form("privacy_form"):
        leaderboard_visible = st.checkbox(
            "Show me on the leaderboard",
            value=leaderboard_visible_val,
        )
        profile_public = st.checkbox(
            "Make my profile public",
            value=profile_public_val,
        )

        save_privacy = st.form_submit_button("Save Privacy Settings", type="primary")

    if save_privacy:
        try:
            with get_db() as s:
                p = s.query(Profile).filter_by(user_id=user_id).first()
                if p:
                    p.leaderboard_visible = leaderboard_visible
                    p.profile_public = profile_public
            st.success("Privacy settings saved!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save: {e}")

    st.markdown("---")
    st.markdown("#### GitHub connection")
    st.markdown(clean_html("""
<div class="alert-info">
    GitHub OAuth is not yet configured. When connected, RepoCompass can verify 
    your PR contributions. We never ask for your GitHub password.
</div>
"""), unsafe_allow_html=True)
    st.button("Connect GitHub (coming soon)", disabled=True)


# ─── Model & Cloud tab ───────────────────────────────────────────────────

with tab_model:
    st.markdown("#### Cloud & Database Status")

    db_info = get_db_info()
    sb_online = is_supabase_online()

    chk_green = icon("check_circle", 16, "#21866D")
    err_red = icon("alert_circle", 16, "#C94C4C")
    db_svg = icon("database", 16, "#159A8C")

    col_sb, col_db = st.columns(2)
    with col_sb:
        if sb_online:
            st.markdown(clean_html(f"""
<div style="background:rgba(33,134,109,0.06);border:1px solid rgba(33,134,109,0.2);border-radius:8px;padding:1rem;">
    <div style="font-weight:600;color:#21866D;display:flex;align-items:center;gap:6px;">{chk_green} <span>Supabase Auth: ONLINE</span></div>
    <div style="font-size:0.85rem;color:#6B7890;margin-top:0.3rem;">
        URL: <code>{settings.supabase_url}</code><br>
        Status: Connected & Synchronized
    </div>
</div>
"""), unsafe_allow_html=True)
        else:
            st.markdown(clean_html(f"""
<div style="background:rgba(201,76,76,0.06);border:1px solid rgba(201,76,76,0.2);border-radius:8px;padding:1rem;">
    <div style="font-weight:600;color:#C94C4C;display:flex;align-items:center;gap:6px;">{err_red} <span>Supabase Auth: Offline</span></div>
    <div style="font-size:0.85rem;color:#6B7890;margin-top:0.3rem;">
        Check SUPABASE_URL and SUPABASE_ANON_KEY in .env.
    </div>
</div>
"""), unsafe_allow_html=True)

    with col_db:
        st.markdown(clean_html(f"""
<div style="background:rgba(21,154,140,0.06);border:1px solid rgba(21,154,140,0.2);border-radius:8px;padding:1rem;">
    <div style="font-weight:600;color:#159A8C;display:flex;align-items:center;gap:6px;">{db_svg} <span>Database: {db_info['type']}</span></div>
    <div style="font-size:0.85rem;color:#6B7890;margin-top:0.3rem;">
        Target: <code>{db_info['url_masked']}</code>
    </div>
</div>
"""), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### AI Model Status")

    if st.button("Recheck Ollama connection", key="recheck_ollama"):
        reset_ollama_cache()

    ollama_ok = check_ollama_available()
    if ollama_ok:
        st.markdown(clean_html(f"""
<div style="background:rgba(33,134,109,0.06);border:1px solid rgba(33,134,109,0.2);border-radius:8px;padding:1rem;">
    <div style="font-weight:600;color:#21866D;display:flex;align-items:center;gap:6px;">{chk_green} <span>Ollama is running</span></div>
    <div style="font-size:0.85rem;color:#6B7890;margin-top:0.3rem;">
        URL: <code>{settings.ollama_base_url}</code><br>
        Model: <code>{settings.ollama_model}</code>
    </div>
</div>
"""), unsafe_allow_html=True)

        models = list_available_models()
        if models:
            st.markdown("**Available models:**")
            for m in models:
                active = "← active" if m.startswith(settings.ollama_model.split(":")[0]) else ""
                st.markdown(f"- `{m}` {active}")
        else:
            st.markdown(f"*No models found. Pull the configured model: `ollama pull {settings.ollama_model}`*")
    else:
        st.markdown(clean_html(f"""
<div style="background:rgba(201,76,76,0.06);border:1px solid rgba(201,76,76,0.2);border-radius:8px;padding:1rem;">
    <div style="font-weight:600;color:#C94C4C;display:flex;align-items:center;gap:6px;">{err_red} <span>Ollama is not reachable</span></div>
    <div style="font-size:0.85rem;color:#6B7890;margin-top:0.3rem;">
        Expected at: <code>{settings.ollama_base_url}</code>
    </div>
</div>
"""), unsafe_allow_html=True)

        st.markdown(f"""
**To start Ollama:**
```bash
ollama serve
ollama pull {settings.ollama_model}
```
""")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Configuration")
    st.markdown(f"""
| Setting | Value |
|---|---|
| Model | `{settings.ollama_model}` |
| Timeout | {settings.model_timeout_seconds}s |
| Max retries | {settings.model_max_retries} |
| Max context chars | {settings.max_context_chars:,} |
| Runner enabled | {'Yes' if settings.runner_enabled else 'No (static review only)'} |

*Change these in your `.env` file.*
""")

    if last_llm_stats:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Last Model Call (measured)")
        st.markdown(f"""
| Metric | Value |
|---|---|
| Model | `{last_llm_stats.get('model', '—')}` |
| Model load | {last_llm_stats.get('load_ms', 0):,.0f} ms |
| Prompt tokens | {last_llm_stats.get('prompt_tokens', 0):,} |
| Prompt (prefill) | {last_llm_stats.get('prompt_ms', 0):,.0f} ms |
| Generated tokens | {last_llm_stats.get('eval_tokens', 0):,} |
| Generation time | {last_llm_stats.get('eval_ms', 0):,.0f} ms |
| Throughput | {last_llm_stats.get('tok_per_s', 0):,.1f} tok/s |
""")
        st.caption("A large **Model load** means the weights were reloaded from disk — keep the model warm with `OLLAMA_KEEP_ALIVE`.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### ⚡ How to Make Ollama Analysis Faster")
    st.markdown(clean_html(f"""
<div style="background:#0F172A;border:1px solid rgba(255,255,255,0.08);border-radius:10px;padding:1.25rem;color:#E2E8F0;">
    <div style="font-weight:700;color:#38BDF8;font-size:1.05rem;margin-bottom:0.75rem;">Proven Strategies for Fast Ollama Inference:</div>
    <ol style="font-size:0.88rem;line-height:1.7;margin:0;padding-left:1.2rem;color:#CBD5E1;">
        <li><strong style="color:#F8FAFC;">Use a Non-Thinking Model (Most Important):</strong> <code>qwen3:4b</code> is a <em>thinking-only</em> model in Ollama that ignores <code>think:false</code>, so it spends the token budget on a reasoning trace. Use the non-thinking variant:
            <br>Run in terminal: <code>ollama pull {settings.ollama_model}</code> (recommended: <code>qwen3:4b-instruct</code>).
        </li>
        <li><strong style="color:#F8FAFC;">Disable Thinking Explicitly (Active):</strong> RepoCompass sends <code>think: false</code> on every request, so no token budget is lost to reasoning.</li>
        <li><strong style="color:#F8FAFC;">Keep Model Hot in RAM (Active):</strong> RepoCompass sends <code>keep_alive: "{settings.ollama_keep_alive}"</code> so weights are not reloaded between calls. You can also set <code>OLLAMA_KEEP_ALIVE=24h</code> before <code>ollama serve</code>.</li>
        <li><strong style="color:#F8FAFC;">Context &amp; Output Bounding (Active):</strong> RepoCompass caps <code>num_ctx: 1536</code> and <code>num_predict: 350</code> with pre-filtered READMEs, reducing token processing dramatically.</li>
        <li><strong style="color:#F8FAFC;">On-Demand Enrichment &amp; Caching (Active):</strong> The deterministic guide renders instantly and AI polish is opt-in. Analyzed repositories are cached, so revisiting loads with 0 Ollama latency.</li>
        <li><strong style="color:#F8FAFC;">GPU / Hardware Offloading:</strong> If an NVIDIA or Apple Silicon GPU is present, Ollama automatically offloads layers. Verify with <code>ollama ps</code> in a terminal.</li>
    </ol>
</div>
"""), unsafe_allow_html=True)


# ─── Data tab ─────────────────────────────────────────────────────────────

with tab_data:
    st.markdown("#### What data we store")
    st.markdown("""
| Data | Purpose |
|---|---|
| Email, display name | Authentication and profile (synced with Supabase Auth) |
| Programming languages, interests | Issue recommendations |
| Experience level | Hint depth calibration |
| XP events (append-only) | Progression tracking |
| Practice session drafts | Your workspace |
| Analyzed repository metadata | Caching |
| Activity log | Dashboard history |

**We do not store:**
- GitHub passwords or tokens in plaintext
- Repository source code beyond the analysis cache
- Private repository content without authorization
- AI conversation history beyond what's in your session
""")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Export your data")
    st.info("Data export is not yet implemented. Contact support for a manual export request.")

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Delete account")
    st.warning("Account deletion removes all your data permanently. This cannot be undone.")
    if st.button("Request Account Deletion", type="secondary"):
        st.error("Account deletion is not yet available via self-service. Please contact support.")
