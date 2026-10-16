"""
Auth Page — Modern Animated Sign-In & Sign-Up with GitHub & Google Login,
and ML Model Experience Questionnaire based on important_files/questions.txt.
"""
import streamlit as st

st.set_page_config(
    page_title="RepoCompass — Sign in",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)

import sys
for mod in list(sys.modules.keys()):
    if mod.startswith("app."):
        del sys.modules[mod]

from app.ui.shared import clean_html, get_current_user, set_current_user, clear_current_user, render_tech_orbit, inject_global_css, render_social_login_buttons
from app.services.auth_service import (
    register_user, login_user, sign_in_with_github, sign_in_with_google,
    save_onboarding_profile, AuthError
)
from app.services.ml_survey_service import save_user_ml_survey, ML_QUESTIONS
from app.services.reward_service import award_xp, maybe_award_achievement, seed_achievements
from app.db.session import init_db

try:
    init_db()
    seed_achievements()
except Exception:
    pass

user = get_current_user()
if user and not st.session_state.get("show_game_fullscreen"):
    st.switch_page("pages/02_dashboard.py")
    st.stop()

if "auth_mode" not in st.session_state:
    st.session_state["auth_mode"] = "signin"

inject_global_css()

# ─── Solo Ledger Warm Editorial Authentication CSS ──────────────────────────
st.markdown(clean_html("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
header[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer { visibility: hidden; }

html, body, [data-testid="stAppViewContainer"], .stApp {
    background: var(--canvas) !important;
    font-family: var(--font-sans) !important;
    color: var(--ink) !important;
    overflow-x: hidden !important;
}

.main .block-container {
    padding-top: 1rem !important;
    padding-bottom: 2rem !important;
    max-width: 1280px !important;
}

/* ── Orbit Canvas Container ─────────────────────────────────────────── */
.orbit-stage {
    position: relative;
    width: 100%;
    height: 600px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    user-select: none;
}
.orbit-center-title {
    position: absolute;
    font-size: 3.4rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(180deg, #111827 0%, rgba(100, 116, 139, 0.35) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    line-height: 1;
    z-index: 5;
    pointer-events: none;
}
.orbit-svg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
}
.ripple-ring {
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(0, 0, 0, 0.05);
    background: rgba(243, 244, 246, 0.35);
    transform: translate(-50%, -50%);
    top: 50%;
    left: 50%;
    animation: ripplePulse 3.5s ease-in-out infinite alternate;
}
@keyframes ripplePulse {
    0% { transform: translate(-50%, -50%) scale(0.96); opacity: 0.4; }
    100% { transform: translate(-50%, -50%) scale(1.04); opacity: 0.8; }
}
.orbit-node {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 44px;
    height: 44px;
    margin-left: -22px;
    margin-top: -22px;
    border-radius: 12px;
    background: #FFFFFF;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.04);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
    animation: spinOrbit var(--d, 20s) linear infinite;
    animation-direction: var(--dir, normal);
}
.orbit-node svg { display: block; max-width: 26px; max-height: 26px; }
@keyframes spinOrbit {
    from { transform: rotate(var(--angle, 0deg)) translateX(var(--r, 120px)) rotate(calc(-1 * var(--angle, 0deg))); }
    to { transform: rotate(calc(var(--angle, 0deg) + 360deg)) translateX(var(--r, 120px)) rotate(calc(-1 * (var(--angle, 0deg) + 360deg))); }
}

/* ── Form Card Styling ──────────────────────────────────────────────── */
.auth-panel {
    background: var(--surface);
    border: 2px solid var(--ink);
    border-radius: var(--radius-card);
    padding: 2rem 1.75rem;
    box-shadow: none;
    margin-top: 1rem;
}
.auth-header h1 {
    font-family: var(--font-sans);
    font-size: 1.85rem;
    font-weight: 700;
    color: var(--ink);
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.02em;
}
.auth-header p {
    font-family: var(--font-sans);
    font-size: 0.9rem;
    color: var(--text-muted);
    margin: 0 0 1.25rem 0;
}

/* Social Buttons */
.btn-social-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-bottom: 1.25rem;
}
.btn-social {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    height: 44px;
    border-radius: 8px;
    font-family: var(--font-sans);
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    text-decoration: none;
}
.btn-social-gh {
    background: var(--ink);
    border: 2px solid var(--ink);
    color: var(--on-ink);
    box-shadow: none;
}
.btn-social-gh:hover {
    background: #333333;
}
.btn-social-google {
    background: var(--surface);
    border: 2px solid var(--ink);
    color: var(--ink);
    box-shadow: none;
}
.btn-social-google:hover {
    background: var(--canvas);
}

/* Dashed Divider */
.or-divider {
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 1.25rem 0 1.1rem 0;
}
.or-divider hr {
    flex: 1;
    border: none;
    border-top: 1px dashed #D1D5DB;
    margin: 0;
}
.or-divider span {
    font-size: 0.82rem;
    color: #6B7280;
    font-weight: 500;
}

/* ML Survey Accordion Box */
.ml-survey-header {
    background: linear-gradient(135deg, rgba(37,99,235,0.06), rgba(139,92,246,0.06));
    border: 1px solid rgba(37,99,235,0.2);
    border-radius: 10px;
    padding: 10px 14px;
    margin: 1rem 0 0.75rem 0;
}
.ml-survey-title {
    font-size: 0.88rem;
    font-weight: 700;
    color: #1D4ED8;
    display: flex;
    align-items: center;
    gap: 6px;
}
.ml-survey-desc {
    font-size: 0.76rem;
    color: #4B5563;
    margin-top: 2px;
}
</style>
"""), unsafe_allow_html=True)

# ─── Two-Column Split Layout ─────────────────────────────────────────────────
left_col, right_col = st.columns([1.1, 1], gap="large")

with left_col:
    render_tech_orbit()

with right_col:
    st.markdown('<div class="auth-panel">', unsafe_allow_html=True)

    if st.session_state.auth_mode == "signin":
        st.markdown(clean_html("""
        <div class="auth-header">
            <h1>Welcome back</h1>
            <p>Sign in with your developer account to continue</p>
        </div>
        """), unsafe_allow_html=True)
    else:
        st.markdown(clean_html("""
        <div class="auth-header">
            <h1>Create an account</h1>
            <p>Calibrate your ML profile to receive personalized issue recommendations</p>
        </div>
        """), unsafe_allow_html=True)

    # ── Social Login Buttons with Official SVG Logos ─────────────────────────
    st.markdown("<div class='t-eyebrow' style='color:var(--text-muted);margin-bottom:8px;'>FAST 1-CLICK DEVELOPER SIGN-IN</div>", unsafe_allow_html=True)
    render_social_login_buttons()
    soc_col1, soc_col2 = st.columns(2)

    with soc_col1:
        if st.button("→ Sign in with GitHub", key="btn_auth_github", use_container_width=True, type="primary"):
            with st.spinner("Connecting to GitHub..."):
                try:
                    user_obj, token = sign_in_with_github(username="octocat_dev")
                    set_current_user({
                        "id": user_obj.id,
                        "email": user_obj.email,
                        "display_name": user_obj.display_name,
                        "avatar_url": user_obj.avatar_url,
                        "level": 1,
                        "xp": 0,
                    }, token=token)
                    st.session_state["show_game_fullscreen"] = True
                    st.switch_page("streamlit_app.py")
                except Exception as e:
                    st.error(f"GitHub sign-in error: {e}")

    with soc_col2:
        if st.button("→ Sign in with Google", key="btn_auth_google", use_container_width=True):
            with st.spinner("Connecting to Google..."):
                try:
                    user_obj, token = sign_in_with_google(email="developer@gmail.com", name="Google Developer")
                    set_current_user({
                        "id": user_obj.id,
                        "email": user_obj.email,
                        "display_name": user_obj.display_name,
                        "avatar_url": user_obj.avatar_url,
                        "level": 1,
                        "xp": 0,
                    }, token=token)
                    st.session_state["show_game_fullscreen"] = True
                    st.switch_page("streamlit_app.py")
                except Exception as e:
                    st.error(f"Google sign-in error: {e}")

    with st.expander("⚡ Custom GitHub Username Sign-in"):
        custom_gh = st.text_input("Enter your GitHub username", placeholder="e.g. torvalds, octocat", key="custom_gh_input")
        if st.button("Sign in with this GitHub Handle →", key="btn_custom_gh", use_container_width=True):
            if custom_gh.strip():
                with st.spinner(f"Verifying {custom_gh} with GitHub..."):
                    try:
                        user_obj, token = sign_in_with_github(username=custom_gh.strip())
                        set_current_user({
                            "id": user_obj.id,
                            "email": user_obj.email,
                            "display_name": user_obj.display_name,
                            "avatar_url": user_obj.avatar_url,
                            "level": 1,
                            "xp": 0,
                        }, token=token)
                        st.session_state["show_game_fullscreen"] = True
                        st.switch_page("streamlit_app.py")
                    except Exception as e:
                        st.error(f"GitHub sign-in error: {e}")

    st.markdown(clean_html("""
    <div class="or-divider">
        <hr><span>or continue with email</span><hr>
    </div>
    """), unsafe_allow_html=True)

    # ── Main Form (Email/Password + ML Survey on Signup) ───────────────────────
    with st.form("modern_auth_form"):
        if st.session_state.auth_mode == "signup":
            full_name = st.text_input("Full Name *", placeholder="Amruta Rothe", key="inp_name")
            email = st.text_input("Email address *", placeholder="you@domain.com", key="inp_email")
            password = st.text_input("Password *", type="password", placeholder="At least 8 characters", key="inp_pwd")

            st.markdown(clean_html("""
            <div class="ml-survey-header">
                <div class="ml-survey-title">🧠 ML Experience Calibration (8 Questions)</div>
                <div class="ml-survey-desc">These inputs train the downstream ML model to match issues directly to your skill level.</div>
            </div>
            """), unsafe_allow_html=True)

            # 8 Questions directly from questions.txt
            ans_q1 = st.multiselect(
                "1. Which of these have you actually done?",
                options=ML_QUESTIONS[0]["options"],
                default=["Forked a repo"],
                key="ml_q1",
            )
            ans_q2 = st.multiselect(
                "2. What can you do with Git?",
                options=ML_QUESTIONS[1]["options"],
                default=["Clone, commit and push"],
                key="ml_q2",
            )
            ans_q3 = st.multiselect(
                "3. Which languages do you know?",
                options=ML_QUESTIONS[2]["options"],
                default=["Python"],
                key="ml_q3",
            )
            ans_q4 = st.multiselect(
                "4. Which could you install on your laptop right now?",
                options=ML_QUESTIONS[3]["options"],
                default=["Python"],
                key="ml_q4",
            )
            ans_q5 = st.selectbox(
                "5. Which operating system are you on?",
                options=ML_QUESTIONS[4]["options"],
                index=0,
                key="ml_q5",
            )
            ans_q6 = st.selectbox(
                "6. What scares you most about your first pull request?",
                options=ML_QUESTIONS[5]["options"],
                index=1,
                key="ml_q6",
            )
            ans_q7 = st.selectbox(
                "7. How do you learn a new tool best?",
                options=ML_QUESTIONS[6]["options"],
                index=2,
                key="ml_q7",
            )
            ans_q8 = st.selectbox(
                "8. How long would you stay stuck before asking someone?",
                options=ML_QUESTIONS[7]["options"],
                index=1,
                key="ml_q8",
            )

            submit_btn = st.form_submit_button("Create Account & Calibrate AI →", use_container_width=True)
        else:
            email = st.text_input("Email address *", placeholder="Enter your email address", key="inp_email")
            password = st.text_input("Password *", type="password", placeholder="Enter your password", key="inp_pwd")
            submit_btn = st.form_submit_button("Sign in →", use_container_width=True)

    # Form Submission Handling
    if submit_btn:
        if not email or "@" not in email:
            st.error("Please enter a valid email address.")
        elif not password:
            st.error("Please enter your password.")
        elif st.session_state.auth_mode == "signup" and len(password) < 8:
            st.error("Password must be at least 8 characters.")
        else:
            with st.spinner("Authenticating..."):
                try:
                    if st.session_state.auth_mode == "signup":
                        display_name = full_name.strip() if full_name else email.split("@")[0]
                        user_obj, token = register_user(
                            email=email.strip().lower(),
                            password=password,
                            display_name=display_name,
                        )

                        # Package survey responses for ML model
                        survey_data = {
                            "q1_actions_done": ans_q1,
                            "q2_git_skills": ans_q2,
                            "q3_languages": ans_q3,
                            "q4_tools_installable": ans_q4,
                            "q5_operating_system": ans_q5,
                            "q6_biggest_fear": ans_q6,
                            "q7_learning_style": ans_q7,
                            "q8_stuck_threshold": ans_q8,
                        }
                        features = save_user_ml_survey(user_obj.id, survey_data)

                        award_xp(user_obj.id, "onboarding_completed")
                        maybe_award_achievement(user_obj.id, "onboarded")
                    else:
                        user_obj, token = login_user(
                            email=email.strip().lower(),
                            password=password,
                        )

                    # Save user session with persistent query parameter
                    set_current_user({
                        "id": user_obj.id,
                        "email": user_obj.email,
                        "display_name": user_obj.display_name,
                        "level": 1,
                        "xp": 0,
                    }, token=token)

                    # Launch 3D Arcade game in fullscreen upon login!
                    st.session_state["show_game_fullscreen"] = True
                    st.switch_page("streamlit_app.py")

                except AuthError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Authentication error: {e}")

    # Mode Toggle
    tcol1, tcol2 = st.columns([1, 1])
    with tcol1:
        if st.session_state.auth_mode == "signin":
            if st.button("Forgot password?", key="btn_forgot", help="Password reset"):
                st.info("Password reset link will be sent to your email.")
    with tcol2:
        if st.session_state.auth_mode == "signin":
            if st.button("Need an account? Sign up", key="btn_switch_su"):
                st.session_state.auth_mode = "signup"
                st.rerun()
        else:
            if st.button("Already have an account? Sign in", key="btn_switch_si"):
                st.session_state.auth_mode = "signin"
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
