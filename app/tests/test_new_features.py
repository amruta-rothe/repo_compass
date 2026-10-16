"""
Tests for new features:
1. GitHub & Google sign-in methods
2. ML survey feature extraction and persistence
3. Guide database caching
"""
import pytest
from app.services.ml_survey_service import (
    ML_QUESTIONS,
    extract_ml_feature_vector,
    save_user_ml_survey,
    get_user_ml_survey,
)
from app.services.auth_service import (
    sign_in_with_github,
    sign_in_with_google,
)
from app.services.guide_generator import (
    save_cached_guide,
    get_cached_guide,
)


def test_ml_questions_definition():
    assert len(ML_QUESTIONS) == 8
    q_ids = [q["id"] for q in ML_QUESTIONS]
    assert "q1_actions_done" in q_ids
    assert "q2_git_skills" in q_ids
    assert "q3_languages" in q_ids
    assert "q4_tools_installable" in q_ids
    assert "q5_operating_system" in q_ids
    assert "q6_biggest_fear" in q_ids
    assert "q7_learning_style" in q_ids
    assert "q8_stuck_threshold" in q_ids


def test_extract_ml_feature_vector_beginner():
    survey = {
        "q1_actions_done": ["None"],
        "q2_git_skills": ["Nothing yet"],
        "q3_languages": ["Python"],
        "q4_tools_installable": ["None of them"],
        "q5_operating_system": "Windows",
        "q6_biggest_fear": "Breaking something",
        "q7_learning_style": "Show me an example",
        "q8_stuck_threshold": "10 minutes",
    }
    vec = extract_ml_feature_vector(survey)
    assert vec["calibrated_tier"] == "beginner"
    assert vec["open_source_score"] == 0.0
    assert vec["git_skill_score"] == 0.0
    assert vec["stuck_threshold_hours"] == 0.16
    assert isinstance(vec["feature_array"], list)


def test_extract_ml_feature_vector_advanced():
    survey = {
        "q1_actions_done": [
            "Forked a repo",
            "Opened an issue",
            "Read someone else’s code for 30+ minutes",
            "Reviewed a pull request",
            "Made a pull request that was merged",
        ],
        "q2_git_skills": [
            "Clone, commit and push",
            "Create branches and pull requests",
            "Resolve merge conflicts",
        ],
        "q3_languages": ["Python", "Rust", "Go", "JavaScript/TypeScript"],
        "q4_tools_installable": ["Python", "Node.js", "Docker"],
        "q5_operating_system": "Linux",
        "q6_biggest_fear": "Picking the wrong issue",
        "q7_learning_style": "Explain the why",
        "q8_stuck_threshold": "Half a day",
    }
    vec = extract_ml_feature_vector(survey)
    assert vec["calibrated_tier"] == "advanced"
    assert vec["git_skill_score"] == 1.0
    assert vec["open_source_score"] >= 0.90
    assert vec["languages_multi_hot"]["Python"] == 1
    assert vec["languages_multi_hot"]["Rust"] == 1


def test_social_auth_github_and_google():
    # Test GitHub login
    gh_user, gh_token = sign_in_with_github("octocat_dev")
    assert gh_user is not None
    assert gh_token is not None
    gh_email = getattr(gh_user, "email", "")
    gh_name = getattr(gh_user, "display_name", "")
    assert "octocat_dev" in gh_email.lower() or "octocat_dev" in gh_name.lower()

    # Test Google login
    g_user, g_token = sign_in_with_google("testuser@gmail.com")
    assert g_user is not None
    assert g_token is not None
    g_email = getattr(g_user, "email", "")
    assert g_email == "testuser@gmail.com"


def test_guide_database_caching():
    repo_name = "test-owner/test-cache-repo"
    guide_body = "# Test Generated Architecture Guide\n\nFast cached guide content."
    save_cached_guide(repo_name, guide_body, model_name="test-ollama")

    retrieved = get_cached_guide(repo_name)
    assert retrieved == guide_body
