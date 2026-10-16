"""
ML Survey Service — Manages onboarding questionnaire and feature engineering
for the downstream Issue Recommendation Machine Learning model.
Questions based on important_files/questions.txt.
"""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.db.session import get_db
from app.db.models import Profile, User


# ─── Questions Definition (Source: important_files/questions.txt) ─────────────

ML_QUESTIONS = [
    {
        "id": "q1_actions_done",
        "number": 1,
        "type": "multiselect",
        "title": "Which of these have you actually done?",
        "subtitle": "Pick all that apply to calibrate your baseline open-source familiarity.",
        "options": [
            "Forked a repo",
            "Opened an issue",
            "Read someone else’s code for 30+ minutes",
            "Reviewed a pull request",
            "Made a pull request that was merged",
            "None",
        ],
        "default": ["Forked a repo"],
    },
    {
        "id": "q2_git_skills",
        "number": 2,
        "type": "multiselect",
        "title": "What can you do with Git?",
        "subtitle": "Pick all that apply to help us suggest the right issue complexity.",
        "options": [
            "Nothing yet",
            "Clone, commit and push",
            "Create branches and pull requests",
            "Resolve merge conflicts",
        ],
        "default": ["Clone, commit and push"],
    },
    {
        "id": "q3_languages",
        "number": 3,
        "type": "multiselect",
        "title": "Which languages do you know?",
        "subtitle": "Select languages you are comfortable reading or writing.",
        "options": [
            "Python",
            "Java",
            "JavaScript/TypeScript",
            "C/C++",
            "Go",
            "Rust",
            "HTML/CSS",
            "Other",
        ],
        "default": ["Python"],
    },
    {
        "id": "q4_tools_installable",
        "number": 4,
        "type": "multiselect",
        "title": "Which could you install on your laptop right now?",
        "subtitle": "Indicates your local environment setup feasibility.",
        "options": [
            "Python",
            "Node.js",
            "Java JDK",
            "Docker",
            "None of them",
        ],
        "default": ["Python"],
    },
    {
        "id": "q5_operating_system",
        "number": 5,
        "type": "select",
        "title": "Which operating system are you on?",
        "subtitle": "Allows us to filter out platform-incompatible dependencies.",
        "options": [
            "Windows",
            "macOS",
            "Linux",
        ],
        "default": "Windows",
    },
    {
        "id": "q6_biggest_fear",
        "number": 6,
        "type": "select",
        "title": "What scares you most about your first pull request?",
        "subtitle": "Tailors the psychological tone and scaffolding of our AI guidance.",
        "options": [
            "Maintainers judging me",
            "Breaking something",
            "Not understanding the code",
            "Git commands",
            "Picking the wrong issue",
        ],
        "default": "Breaking something",
    },
    {
        "id": "q7_learning_style",
        "number": 7,
        "type": "select",
        "title": "How do you learn a new tool best?",
        "subtitle": "Calibrates how adaptive hints are formatted.",
        "options": [
            "Short steps",
            "Explain the why",
            "Show me an example",
            "Link me to a video",
        ],
        "default": "Show me an example",
    },
    {
        "id": "q8_stuck_threshold",
        "number": 8,
        "type": "select",
        "title": "How long would you stay stuck before asking someone?",
        "subtitle": "Helps our system recommend hints before frustration kicks in.",
        "options": [
            "10 minutes",
            "1 hour",
            "Half a day",
            "I’d never ask",
        ],
        "default": "1 hour",
    },
]


# ─── Feature Extraction & Numerical Encoding for ML Model ────────────────────

def extract_ml_feature_vector(survey: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transforms qualitative user responses into normalized, continuous and categorical
    numerical features suitable for training ML models (e.g. Scikit-learn, XGBoost, PyTorch).
    """
    q1 = survey.get("q1_actions_done", [])
    if isinstance(q1, str):
        q1 = [q1]

    # Open Source Experience Score [0.0 - 1.0]
    os_weights = {
        "None": 0.0,
        "Forked a repo": 0.10,
        "Read someone else’s code for 30+ minutes": 0.15,
        "Opened an issue": 0.20,
        "Reviewed a pull request": 0.25,
        "Made a pull request that was merged": 0.35,
    }
    if "None" in q1:
        os_score = 0.0
    else:
        os_score = min(sum(os_weights.get(a, 0.05) for a in q1), 1.0)

    # Git Skill Score [0.0 - 1.0]
    q2 = survey.get("q2_git_skills", [])
    if isinstance(q2, str):
        q2 = [q2]
    git_weights = {
        "Nothing yet": 0.0,
        "Clone, commit and push": 0.30,
        "Create branches and pull requests": 0.35,
        "Resolve merge conflicts": 0.35,
    }
    if "Nothing yet" in q2:
        git_score = 0.0
    else:
        git_score = min(sum(git_weights.get(g, 0.1) for g in q2), 1.0)

    # Tooling readiness [0.0 - 1.0]
    q4 = survey.get("q4_tools_installable", [])
    if isinstance(q4, str):
        q4 = [q4]
    tool_count = len([t for t in q4 if t != "None of them"])
    tools_score = min(tool_count / 4.0, 1.0)

    # Stuck threshold in hours
    stuck_mapping = {
        "10 minutes": 0.16,
        "1 hour": 1.0,
        "Half a day": 4.0,
        "I’d never ask": 24.0,
    }
    stuck_hours = stuck_mapping.get(survey.get("q8_stuck_threshold", "1 hour"), 1.0)

    # OS Categorical ID
    os_map = {"Windows": 0, "macOS": 1, "Linux": 2}
    os_id = os_map.get(survey.get("q5_operating_system", "Windows"), 0)

    # Fear Categorical ID
    fear_map = {
        "Maintainers judging me": 0,
        "Breaking something": 1,
        "Not understanding the code": 2,
        "Git commands": 3,
        "Picking the wrong issue": 4,
    }
    fear_id = fear_map.get(survey.get("q6_biggest_fear", "Breaking something"), 1)

    # Learning Style Categorical ID
    learn_map = {
        "Short steps": 0,
        "Explain the why": 1,
        "Show me an example": 2,
        "Link me to a video": 3,
    }
    learn_id = learn_map.get(survey.get("q7_learning_style", "Show me an example"), 2)

    # Multi-hot Languages Vector
    langs = survey.get("q3_languages", [])
    if isinstance(langs, str):
        langs = [langs]
    standard_langs = ["Python", "Java", "JavaScript/TypeScript", "C/C++", "Go", "Rust", "HTML/CSS"]
    lang_vector = {lang: 1 if any(lang.lower() in str(l).lower() for l in langs) else 0 for lang in standard_langs}

    # Calibrate estimated experience tier
    combined_readiness = (os_score * 0.45) + (git_score * 0.40) + (tools_score * 0.15)
    if combined_readiness >= 0.65:
        tier = "advanced"
    elif combined_readiness >= 0.28:
        tier = "intermediate"
    else:
        tier = "beginner"

    # Flat numerical feature array for direct tabular ML input
    feature_array = [
        round(os_score, 3),
        round(git_score, 3),
        round(tools_score, 3),
        round(stuck_hours, 2),
        os_id,
        fear_id,
        learn_id,
        len(langs),
    ] + [lang_vector[l] for l in standard_langs]

    return {
        "open_source_score": round(os_score, 3),
        "git_skill_score": round(git_score, 3),
        "tools_readiness_score": round(tools_score, 3),
        "stuck_threshold_hours": stuck_hours,
        "os_id": os_id,
        "fear_id": fear_id,
        "learning_style_id": learn_id,
        "languages_multi_hot": lang_vector,
        "calibrated_tier": tier,
        "feature_array": feature_array,
        "feature_names": [
            "open_source_score",
            "git_skill_score",
            "tools_readiness_score",
            "stuck_threshold_hours",
            "os_id",
            "fear_id",
            "learning_style_id",
            "language_count",
        ] + [f"lang_{l.lower().replace('/', '_')}" for l in standard_langs],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def save_user_ml_survey(user_id: str, survey: Dict[str, Any]) -> Dict[str, Any]:
    """
    Saves raw answers and derived ML features into the user's Profile record.
    """
    features = extract_ml_feature_vector(survey)

    with get_db() as session:
        profile = session.query(Profile).filter_by(user_id=user_id).first()
        if not profile:
            profile = Profile(user_id=user_id)
            session.add(profile)

        profile.ml_survey = survey
        profile.ml_features = features
        profile.experience_level = features["calibrated_tier"]

        # Keep legacy profile fields synchronized
        langs = survey.get("q3_languages", [])
        if isinstance(langs, str):
            langs = [langs]
        profile.programming_languages = [l for l in langs if l != "Other"]
        profile.comfortable_with_git = features["git_skill_score"] >= 0.30
        profile.onboarding_completed = True
        profile.updated_at = datetime.now(timezone.utc)
        session.flush()

    return features


def get_user_ml_survey(user_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves user's saved survey and features."""
    with get_db() as session:
        profile = session.query(Profile).filter_by(user_id=user_id).first()
        if not profile:
            return None
        return {
            "survey": profile.ml_survey or {},
            "features": profile.ml_features or {},
            "tier": profile.experience_level or "beginner",
            "languages": profile.programming_languages or [],
        }
