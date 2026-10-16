"""
SQLAlchemy ORM models for RepoCompass.
All timestamps in UTC. No secrets stored in these tables.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer,
    String, Text, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# Users / Profiles
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)  # null when using OAuth
    display_name = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    github_username = Column(String, nullable=True)
    github_access_token_encrypted = Column(String, nullable=True)  # encrypted at rest
    created_at = Column(DateTime(timezone=True), default=_now)
    last_seen_at = Column(DateTime(timezone=True), default=_now)
    is_active = Column(Boolean, default=True)

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    xp_events = relationship("XPEvent", back_populates="user", cascade="all, delete-orphan")
    practice_sessions = relationship("PracticeSession", back_populates="user")
    achievements = relationship("UserAchievement", back_populates="user", cascade="all, delete-orphan")
    skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    activity_events = relationship("ActivityEvent", back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    bio = Column(Text, nullable=True)

    # Onboarding — experience & preferences
    experience_level = Column(String, nullable=True)  # beginner | intermediate | advanced
    years_of_experience = Column(Integer, nullable=True)
    programming_languages = Column(JSON, default=list)   # ["Python", "JavaScript", ...]
    interests = Column(JSON, default=list)               # ["web", "ml", "devops", ...]
    contribution_goals = Column(JSON, default=list)      # ["fix bugs", "add features", ...]
    preferred_issue_types = Column(JSON, default=list)   # ["bug", "docs", "feature", ...]
    open_source_contributions_count = Column(Integer, default=0)
    comfortable_with_testing = Column(Boolean, default=False)
    comfortable_with_git = Column(Boolean, default=True)
    onboarding_completed = Column(Boolean, default=False)
    ml_survey = Column(JSON, default=dict)               # Raw answers from questions.txt
    ml_features = Column(JSON, default=dict)             # Structured encoded feature vector for ML training

    # Gamification
    xp_total = Column(Integer, default=0)
    level = Column(Integer, default=1)
    coins = Column(Integer, default=0)
    current_streak_days = Column(Integer, default=0)
    longest_streak_days = Column(Integer, default=0)
    last_activity_date = Column(String, nullable=True)  # ISO date

    # Privacy
    profile_public = Column(Boolean, default=True)
    leaderboard_visible = Column(Boolean, default=False)

    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    user = relationship("User", back_populates="profile")


# ─────────────────────────────────────────────────────────────────────────────
# Repositories & Snapshots
# ─────────────────────────────────────────────────────────────────────────────

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True, default=_uuid)
    owner = Column(String, nullable=False)
    name = Column(String, nullable=False)
    full_name = Column(String, nullable=False, index=True)  # owner/name
    url = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    primary_language = Column(String, nullable=True)
    topics = Column(JSON, default=list)
    stars = Column(Integer, default=0)
    open_issues_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=_now)
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    analysis_status = Column(String, default="pending")  # pending|running|done|failed

    snapshots = relationship("RepositorySnapshot", back_populates="repository", cascade="all, delete-orphan")
    issues = relationship("Issue", back_populates="repository", cascade="all, delete-orphan")
    guides = relationship("Guide", back_populates="repository", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("owner", "name", name="uq_repo_owner_name"),)


class RepositorySnapshot(Base):
    __tablename__ = "repository_snapshots"

    id = Column(String, primary_key=True, default=_uuid)
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    sha = Column(String, nullable=True)           # HEAD commit SHA at time of analysis
    raw_data = Column(JSON, default=dict)          # cached GitHub API response data
    directory_tree = Column(JSON, default=list)    # [{path, type, size}]
    readme_content = Column(Text, nullable=True)
    contributing_content = Column(Text, nullable=True)
    dependency_files = Column(JSON, default=dict)  # {filename: content}
    fetched_at = Column(DateTime(timezone=True), default=_now)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    repository = relationship("Repository", back_populates="snapshots")


# ─────────────────────────────────────────────────────────────────────────────
# Issues
# ─────────────────────────────────────────────────────────────────────────────

class Issue(Base):
    __tablename__ = "issues"

    id = Column(String, primary_key=True, default=_uuid)
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    github_id = Column(Integer, nullable=False)
    number = Column(Integer, nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=True)
    state = Column(String, default="open")
    labels = Column(JSON, default=list)
    assignees = Column(JSON, default=list)
    author = Column(String, nullable=True)
    html_url = Column(String, nullable=False)
    comments_count = Column(Integer, default=0)
    created_at_gh = Column(DateTime(timezone=True), nullable=True)
    updated_at_gh = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), default=_now)

    repository = relationship("Repository", back_populates="issues")
    score = relationship("IssueScore", back_populates="issue", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("repository_id", "number", name="uq_issue_repo_number"),
        Index("ix_issue_repo_state", "repository_id", "state"),
    )


class IssueScore(Base):
    __tablename__ = "issue_scores"

    id = Column(String, primary_key=True, default=_uuid)
    issue_id = Column(String, ForeignKey("issues.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_score = Column(Float, default=0.0)
    difficulty_estimate = Column(String, nullable=True)  # beginner|intermediate|advanced
    signals = Column(JSON, default=dict)   # {signal_name: {value, weight, reason}}
    explanation = Column(Text, nullable=True)
    computed_at = Column(DateTime(timezone=True), default=_now)

    issue = relationship("Issue", back_populates="score")


# ─────────────────────────────────────────────────────────────────────────────
# Guides & Evidence
# ─────────────────────────────────────────────────────────────────────────────

class Guide(Base):
    __tablename__ = "guides"

    id = Column(String, primary_key=True, default=_uuid)
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    snapshot_id = Column(String, ForeignKey("repository_snapshots.id"), nullable=True)
    model_name = Column(String, nullable=True)
    content = Column(JSON, default=dict)   # structured sections
    status = Column(String, default="generating")  # generating|done|failed
    generated_at = Column(DateTime(timezone=True), default=_now)

    evidence_refs = relationship("EvidenceRef", back_populates="guide", cascade="all, delete-orphan")
    repository = relationship("Repository", back_populates="guides")


class EvidenceRef(Base):
    __tablename__ = "evidence_refs"

    id = Column(String, primary_key=True, default=_uuid)
    guide_id = Column(String, ForeignKey("guides.id", ondelete="CASCADE"), nullable=False)
    claim_key = Column(String, nullable=False)   # section + claim identifier
    source_type = Column(String, nullable=True)  # readme|contributing|issue|file|github_api
    source_path = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    verified = Column(Boolean, default=False)

    guide = relationship("Guide", back_populates="evidence_refs")


# ─────────────────────────────────────────────────────────────────────────────
# Practice Sessions
# ─────────────────────────────────────────────────────────────────────────────

class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    issue_id = Column(String, ForeignKey("issues.id"), nullable=True)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    status = Column(String, default="active")  # active|completed|abandoned
    patch_draft = Column(Text, nullable=True)
    ai_review = Column(Text, nullable=True)
    hint_level_reached = Column(Integer, default=0)
    hints_used = Column(JSON, default=list)
    started_at = Column(DateTime(timezone=True), default=_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="practice_sessions")
    runs = relationship("PracticeRun", back_populates="session", cascade="all, delete-orphan")


class PracticeRun(Base):
    __tablename__ = "practice_runs"

    id = Column(String, primary_key=True, default=_uuid)
    session_id = Column(String, ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False)
    run_type = Column(String, default="static_review")  # static_review|isolated_run
    status = Column(String, default="not_run")  # not_run|running|passed|failed|unavailable
    output = Column(Text, nullable=True)   # escaped, untrusted
    started_at = Column(DateTime(timezone=True), default=_now)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    session = relationship("PracticeSession", back_populates="runs")


# ─────────────────────────────────────────────────────────────────────────────
# Gamification
# ─────────────────────────────────────────────────────────────────────────────

class XPEvent(Base):
    __tablename__ = "xp_events"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    xp_awarded = Column(Integer, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=False)  # prevents duplicates
    event_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", back_populates="xp_events")


class Achievement(Base):
    __tablename__ = "achievements"

    id = Column(String, primary_key=True, default=_uuid)
    key = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String, default="trophy")
    xp_reward = Column(Integer, default=0)
    condition_type = Column(String, nullable=True)
    condition_value = Column(JSON, default=dict)


class UserAchievement(Base):
    __tablename__ = "user_achievements"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    achievement_id = Column(String, ForeignKey("achievements.id"), nullable=False)
    awarded_at = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", back_populates="achievements")
    achievement = relationship("Achievement")

    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_name = Column(String, nullable=False)
    evidence_count = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="skills")

    __table_args__ = (UniqueConstraint("user_id", "skill_name", name="uq_user_skill"),)


# ─────────────────────────────────────────────────────────────────────────────
# Activity
# ─────────────────────────────────────────────────────────────────────────────

class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    event_metadata = Column(JSON, default=dict)
    occurred_at = Column(DateTime(timezone=True), default=_now)

    user = relationship("User", back_populates="activity_events")


# ─────────────────────────────────────────────────────────────────────────────
# Maintainer Studio
# ─────────────────────────────────────────────────────────────────────────────

class MaintainerDraft(Base):
    __tablename__ = "maintainer_drafts"

    id = Column(String, primary_key=True, default=_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    repository_id = Column(String, ForeignKey("repositories.id"), nullable=False)
    issue_id = Column(String, ForeignKey("issues.id"), nullable=True)
    draft_type = Column(String, nullable=False)  # improvement|starter_issue|related
    title = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    rationale = Column(Text, nullable=True)
    status = Column(String, default="draft")  # draft|approved|discarded|copied
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
