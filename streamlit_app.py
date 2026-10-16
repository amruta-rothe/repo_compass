"""
RepoCompass — Root Entry Point.
Initial state: Clean, high-contrast Sign-In / Sign-Up page with GitHub & Google Login.
Post-auth: Directly launches the 3D Sakura Trail Arcade Game in pure fullscreen.
Pressing ESC inside the game opens a navigation menu to Skip to Dashboard or Sign Out.
"""
import os
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="RepoCompass — Welcome",
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

from app.ui.sakura_runner import render_sakura_game

# Handle action callbacks from the embedded 3D WebGL game
if st.query_params.get("game_action") == "dashboard":
    del st.query_params["game_action"]
    st.session_state["show_game_fullscreen"] = False
    st.switch_page("pages/02_dashboard.py")
elif st.query_params.get("game_action") == "signout":
    del st.query_params["game_action"]
    clear_current_user()
    st.session_state["show_game_fullscreen"] = False
    st.rerun()

user = get_current_user()

# ─── Case 1: Post-Auth Fullscreen 3D Sakura Trail Arcade Mode ───────────────
if user and st.session_state.get("show_game_fullscreen"):
    # Header bar with floating quick-skip for zero-friction navigation
    st.markdown(clean_html("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    #MainMenu, footer { visibility: hidden !important; }
    .main .block-container {
        padding: 0.5rem 1rem 0 1rem !important;
        margin: 0 !important;
        max-width: 100vw !important;
        overflow: hidden !important;
    }
    iframe {
        width: 100vw !important;
        height: 92vh !important;
        border: none !important;
        display: block !important;
    }
    </style>
    """), unsafe_allow_html=True)

    # Sleek Solo Ledger floating HUD bar
    st.markdown(clean_html("""
    <div style="background:var(--topbar,#214F4B);border-bottom:2px solid var(--ink,#111);padding:8px 1.5rem;display:flex;align-items:center;justify-content:space-between;margin:-0.5rem -1rem 0.5rem -1rem;">
        <div style="font-family:var(--font-mono,'JetBrains Mono',monospace);font-size:11px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:var(--topbar-text,#E8F1EC);">
            🌸 SAKURA TRAIL — Press <code style="background:rgba(255,255,255,0.15);border-radius:3px;padding:1px 5px;">ESC</code> in game or click to skip
        </div>
    </div>
    """), unsafe_allow_html=True)
    hud_c1, hud_c2 = st.columns([1, 1])
    with hud_c1:
        if st.button("→ Skip to Dashboard", key="game_hud_skip", type="primary", use_container_width=True):
            st.session_state["show_game_fullscreen"] = False
            st.switch_page("pages/02_dashboard.py")
    with hud_c2:
        if st.button("← Sign Out", key="game_hud_signout", use_container_width=True):
            clear_current_user()
            st.session_state["show_game_fullscreen"] = False
            st.switch_page("pages/01_auth.py")

    action = render_sakura_game(key="sakura_canvas")
    if action == "dashboard":
        st.session_state["show_game_fullscreen"] = False
        st.switch_page("pages/02_dashboard.py")
    elif action == "signout":
        clear_current_user()
        st.session_state["show_game_fullscreen"] = False
        st.switch_page("pages/01_auth.py")
    elif isinstance(action, str) and action.startswith("gate:"):
        target = action.replace("gate:", "")
        st.session_state["show_game_fullscreen"] = False
        st.switch_page(target)
    st.stop()


# ─── Case 2: Already Logged In (Quick Switch to Dashboard) ───────────────────
if user and not st.session_state.get("show_game_fullscreen"):
    st.switch_page("pages/02_dashboard.py")
    st.stop()


# ─── Case 3: Initial Website Entry — Modern Sign-In & Sign-Up ────────────────
if "auth_mode" not in st.session_state:
    st.session_state["auth_mode"] = "signin"

inject_global_css()

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
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
    max-width: 1280px !important;
}

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

.or-divider {
    display: flex;
    align-items: center;
    gap: 14px;
    margin: 1.25rem 0 1.1rem 0;
}
.or-divider hr {
    flex: 1;
    border: none;
    border-top: 1px dashed var(--ink);
    margin: 0;
}
.or-divider span {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--text-muted);
    font-weight: 600;
}

.ml-survey-header {
    background: var(--mint);
    border: 2px solid var(--ink);
    border-radius: 8px;
    padding: 10px 14px;
    margin: 1rem 0 0.75rem 0;
}
.ml-survey-title {
    font-family: var(--font-sans);
    font-size: 0.88rem;
    font-weight: 700;
    color: var(--ink);
    display: flex;
    align-items: center;
    gap: 6px;
}
.ml-survey-desc {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--ink);
    margin-top: 2px;
}
</style>
"""), unsafe_allow_html=True)

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
        if st.button("→ Sign in with GitHub", key="root_btn_auth_github", use_container_width=True, type="primary"):
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
                    st.rerun()
                except Exception as e:
                    st.error(f"GitHub sign-in error: {e}")

    with soc_col2:
        if st.button("→ Sign in with Google", key="root_btn_auth_google", use_container_width=True):
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
                    st.rerun()
                except Exception as e:
                    st.error(f"Google sign-in error: {e}")

    with st.expander("⚡ Custom GitHub Username Sign-in"):
        custom_gh = st.text_input("Enter your GitHub username", placeholder="e.g. torvalds, octocat", key="root_custom_gh_input")
        if st.button("Sign in with this GitHub Handle →", key="root_btn_custom_gh", use_container_width=True):
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
                        st.rerun()
                    except Exception as e:
                        st.error(f"GitHub sign-in error: {e}")

    st.markdown(clean_html("""
    <div class="or-divider">
        <hr><span>or continue with email</span><hr>
    </div>
    """), unsafe_allow_html=True)

    # ── Main Form ─────────────────────────────────────────────────────────────
    with st.form("modern_auth_form_root"):
        if st.session_state.auth_mode == "signup":
            full_name = st.text_input("Full Name *", placeholder="Amruta Rothe", key="root_inp_name")
            email = st.text_input("Email address *", placeholder="you@domain.com", key="root_inp_email")
            password = st.text_input("Password *", type="password", placeholder="At least 8 characters", key="root_inp_pwd")

            st.markdown(clean_html("""
            <div class="ml-survey-header">
                <div class="ml-survey-title">🧠 ML Experience Calibration (8 Questions)</div>
                <div class="ml-survey-desc">These inputs train the downstream ML model to match issues directly to your skill level.</div>
            </div>
            """), unsafe_allow_html=True)

            ans_q1 = st.multiselect(
                "1. Which of these have you actually done?",
                options=ML_QUESTIONS[0]["options"],
                default=["Forked a repo"],
                key="root_ml_q1",
            )
            ans_q2 = st.multiselect(
                "2. What can you do with Git?",
                options=ML_QUESTIONS[1]["options"],
                default=["Clone, commit and push"],
                key="root_ml_q2",
            )
            ans_q3 = st.multiselect(
                "3. Which languages do you know?",
                options=ML_QUESTIONS[2]["options"],
                default=["Python"],
                key="root_ml_q3",
            )
            ans_q4 = st.multiselect(
                "4. Which could you install on your laptop right now?",
                options=ML_QUESTIONS[3]["options"],
                default=["Python"],
                key="root_ml_q4",
            )
            ans_q5 = st.selectbox(
                "5. Which operating system are you on?",
                options=ML_QUESTIONS[4]["options"],
                index=0,
                key="root_ml_q5",
            )
            ans_q6 = st.selectbox(
                "6. What scares you most about your first pull request?",
                options=ML_QUESTIONS[5]["options"],
                index=1,
                key="root_ml_q6",
            )
            ans_q7 = st.selectbox(
                "7. How do you learn a new tool best?",
                options=ML_QUESTIONS[6]["options"],
                index=2,
                key="root_ml_q7",
            )
            ans_q8 = st.selectbox(
                "8. How long would you stay stuck before asking someone?",
                options=ML_QUESTIONS[7]["options"],
                index=1,
                key="root_ml_q8",
            )

            submit_btn = st.form_submit_button("Create Account & Calibrate AI →", use_container_width=True)
        else:
            email = st.text_input("Email address *", placeholder="Enter your email address", key="root_inp_email")
            password = st.text_input("Password *", type="password", placeholder="Enter your password", key="root_inp_pwd")
            submit_btn = st.form_submit_button("Sign in →", use_container_width=True)

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
                        save_user_ml_survey(user_obj.id, survey_data)
                        award_xp(user_obj.id, "onboarding_completed")
                        maybe_award_achievement(user_obj.id, "onboarded")
                    else:
                        user_obj, token = login_user(
                            email=email.strip().lower(),
                            password=password,
                        )

                    set_current_user({
                        "id": user_obj.id,
                        "email": user_obj.email,
                        "display_name": user_obj.display_name,
                        "level": 1,
                        "xp": 0,
                    }, token=token)

                    st.session_state["show_game_fullscreen"] = True
                    st.rerun()

                except AuthError as e:
                    st.error(str(e))
                except Exception as e:
                    st.error(f"Authentication error: {e}")

    tcol1, tcol2 = st.columns([1, 1])
    with tcol1:
        if st.session_state.auth_mode == "signin":
            if st.button("Forgot password?", key="btn_forgot_root", help="Password reset"):
                st.info("Password reset link will be sent to your email.")
    with tcol2:
        if st.session_state.auth_mode == "signin":
            if st.button("Need an account? Sign up", key="btn_switch_su_root"):
                st.session_state.auth_mode = "signup"
                st.rerun()
        else:
            if st.button("Already have an account? Sign in", key="btn_switch_si_root"):
                st.session_state.auth_mode = "signin"
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
