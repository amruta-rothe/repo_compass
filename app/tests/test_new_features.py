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
    login_user,
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
    assert "q7_experience_years" in q_ids


def test_extract_ml_feature_vector_beginner():
    survey = {
        "q1_actions_done": ["None"],
        "q2_git_skills": ["Nothing yet"],
        "q3_languages": ["Python"],
        "q4_goal": "Learn how open source works",
        "q5_first_issue_preference": "Small bug fix with a clear reproduction",
        "q6_weekly_hours": "< 2 hours",
        "q7_experience_years": "< 6 months",
        "q8_work_preference": "No preference",
    }
    vec = extract_ml_feature_vector(survey)
    assert vec["calibrated_tier"] == "beginner"
    assert vec["programming_experience_years"] <= 0.5
    assert vec["git_skill_score"] == 0.0
    assert vec["weekly_hours_available"] == 1.5


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
        "q3_languages": ["Python", "Rust", "Go", "TypeScript"],
        "q4_goal": "Get regular contributions in my target tech stack",
        "q5_first_issue_preference": "Challenging core logic issue",
        "q6_weekly_hours": "10+ hours",
        "q7_experience_years": "3+ years",
        "q8_work_preference": "Code only",
    }
    vec = extract_ml_feature_vector(survey)
    assert vec["calibrated_tier"] == "advanced"
    assert vec["programming_experience_years"] == 4.0
    assert vec["git_skill_score"] == 1.0
    assert vec["wants_code_only"] is True


def test_social_auth_github_and_google():
    # Test GitHub login
    gh_user, gh_token = sign_in_with_github("octocat_dev")
    assert gh_user is not None
    assert gh_token is not None
    assert "github.com" in gh_user["email"] or "octocat_dev" in gh_user["display_name"].lower()

    # Test Google login
    g_user, g_token = sign_in_with_google("testuser@gmail.com")
    assert g_user is not None
    assert g_token is not None
    assert g_user["email"] == "testuser@gmail.com"


def test_guide_database_caching():
    repo_name = "test-owner/test-cache-repo"
    guide_body = "# Test Generated Architecture Guide\n\nFast cached guide content."
    save_cached_guide(repo_name, guide_body, model_name="test-ollama")

    retrieved = get_cached_guide(repo_name)
    assert retrieved == guide_body
