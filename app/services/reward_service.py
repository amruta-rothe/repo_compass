"""
Gamification / reward service — XP events, leveling, achievements.
All calculations are server-side and idempotent.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, date, timezone
from typing import Optional, List, Tuple, Dict

from sqlalchemy.orm import Session

from app.db.models import User, Profile, XPEvent, Achievement, UserAchievement, ActivityEvent
from app.db.session import get_db


# ─── XP thresholds ────────────────────────────────────────────────────────

XP_THRESHOLDS = [0, 100, 300, 600, 1000, 1500, 2200, 3000, 4000, 5500, 7500]
# Level 1 starts at 0 XP; Level 11+ uses 7500 + 2000*(level-11)


def xp_for_level(level: int) -> int:
    if level <= len(XP_THRESHOLDS):
        return XP_THRESHOLDS[level - 1]
    return XP_THRESHOLDS[-1] + 2000 * (level - len(XP_THRESHOLDS))


def level_from_xp(xp: int) -> int:
    for lvl in range(len(XP_THRESHOLDS), 0, -1):
        if xp >= XP_THRESHOLDS[lvl - 1]:
            return lvl
    return 1


def xp_progress(xp: int) -> Tuple[int, int, int]:
    """Returns (current_level, xp_into_level, xp_needed_for_next_level)."""
    level = level_from_xp(xp)
    current_threshold = xp_for_level(level)
    next_threshold = xp_for_level(level + 1)
    return level, xp - current_threshold, next_threshold - current_threshold


# ─── XP event types & amounts ─────────────────────────────────────────────

XP_RULES: Dict[str, int] = {
    "repo_analyzed": 10,
    "first_repo_analyzed": 20,
    "practice_session_started": 5,
    "practice_milestone": 15,
    "pr_opened": 30,
    "pr_merged": 75,
    "first_contribution": 50,
    "review_given": 20,
    "onboarding_completed": 25,
    "streak_3_days": 15,
    "streak_7_days": 40,
}


def _idempotency_key(user_id: str, event_type: str, context: str = "") -> str:
    raw = f"{user_id}:{event_type}:{context}"
    return hashlib.sha256(raw.encode()).hexdigest()


def award_xp(
    user_id: str,
    event_type: str,
    idempotency_context: str = "",
    metadata: Optional[dict] = None,
    db: Optional[Session] = None,
) -> Tuple[int, bool]:
    """
    Award XP for an event. Idempotent — duplicate events are ignored.
    Returns (xp_awarded, was_new_event).
    """
    xp_amount = XP_RULES.get(event_type, 0)
    if xp_amount == 0:
        return 0, False

    ikey = _idempotency_key(user_id, event_type, idempotency_context)

    def _do(session: Session) -> Tuple[int, bool]:
        user_exists = session.query(User).filter_by(id=user_id).first()
        if not user_exists:
            return 0, False

        existing = session.query(XPEvent).filter_by(idempotency_key=ikey).first()
        if existing:
            return xp_amount, False  # duplicate prevented

        event = XPEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type=event_type,
            xp_awarded=xp_amount,
            idempotency_key=ikey,
            event_metadata=metadata or {},
        )
        session.add(event)

        profile = session.query(Profile).filter_by(user_id=user_id).first()
        if profile:
            profile.xp_total += xp_amount
            new_level = level_from_xp(profile.xp_total)
            if new_level != profile.level:
                profile.level = new_level
            _update_streak(profile)

        _log_activity(user_id, event_type, session, metadata)
        session.flush()
        return xp_amount, True

    if db is not None:
        return _do(db)
    with get_db() as session:
        return _do(session)


def _update_streak(profile: Profile):
    from datetime import timedelta
    today = date.today()
    today_str = today.isoformat()
    if profile.last_activity_date == today_str:
        return
    yesterday = (today - timedelta(days=1)).isoformat()
    if profile.last_activity_date == yesterday:
        profile.current_streak_days += 1
    else:
        profile.current_streak_days = 1
    profile.longest_streak_days = max(profile.longest_streak_days, profile.current_streak_days)
    profile.last_activity_date = today_str


def _log_activity(user_id: str, event_type: str, session: Session, metadata: Optional[dict]):
    user_exists = session.query(User).filter_by(id=user_id).first()
    if not user_exists:
        return
    evt = ActivityEvent(
        id=str(uuid.uuid4()),
        user_id=user_id,
        event_type=event_type,
        event_metadata=metadata or {},
    )
    session.add(evt)


# ─── Achievements ──────────────────────────────────────────────────────────

BUILT_IN_ACHIEVEMENTS = [
    {"key": "first_repo", "name": "Repository Explorer", "description": "Analyzed your first repository", "icon": "map", "xp_reward": 20},
    {"key": "first_practice", "name": "Practice Makes Perfect", "description": "Started your first practice session", "icon": "code", "xp_reward": 15},
    {"key": "onboarded", "name": "Compass Calibrated", "description": "Completed onboarding", "icon": "compass", "xp_reward": 25},
    {"key": "streak_3", "name": "Hat Trick", "description": "3-day contribution streak", "icon": "flame", "xp_reward": 15},
    {"key": "streak_7", "name": "Week Warrior", "description": "7-day contribution streak", "icon": "zap", "xp_reward": 40},
    {"key": "first_pr", "name": "Pull Requester", "description": "Opened your first PR", "icon": "sparkles", "xp_reward": 30},
    {"key": "merged_pr", "name": "Merged!", "description": "Had a PR merged", "icon": "award", "xp_reward": 75},
]


def seed_achievements(db: Optional[Session] = None):
    def _seed(session: Session):
        for ach in BUILT_IN_ACHIEVEMENTS:
            existing = session.query(Achievement).filter_by(key=ach["key"]).first()
            if not existing:
                session.add(Achievement(
                    id=str(uuid.uuid4()),
                    key=ach["key"],
                    name=ach["name"],
                    description=ach["description"],
                    icon=ach["icon"],
                    xp_reward=ach["xp_reward"],
                ))

    if db is not None:
        _seed(db)
    else:
        with get_db() as session:
            _seed(session)


def maybe_award_achievement(
    user_id: str,
    achievement_key: str,
    db: Optional[Session] = None,
) -> Optional[Achievement]:
    def _do(session: Session) -> Optional[Achievement]:
        user_exists = session.query(User).filter_by(id=user_id).first()
        if not user_exists:
            return None
        ach = session.query(Achievement).filter_by(key=achievement_key).first()
        if not ach:
            return None
        existing = session.query(UserAchievement).filter_by(
            user_id=user_id, achievement_id=ach.id
        ).first()
        if existing:
            return None
        ua = UserAchievement(
            id=str(uuid.uuid4()),
            user_id=user_id,
            achievement_id=ach.id,
        )
        session.add(ua)
        if ach.xp_reward:
            award_xp(user_id, f"achievement_{achievement_key}", db=session)
        session.flush()
        return ach

    if db is not None:
        return _do(db)
    with get_db() as session:
        return _do(session)


def get_user_progress(user_id: str, db: Optional[Session] = None) -> dict:
    def _get(session: Session) -> dict:
        profile = session.query(Profile).filter_by(user_id=user_id).first()
        if not profile:
            return {"xp": 0, "level": 1, "streak": 0, "achievements": []}

        level, xp_into, xp_needed = xp_progress(profile.xp_total)
        user_achs = (
            session.query(UserAchievement)
            .filter_by(user_id=user_id)
            .all()
        )
        ach_list = []
        for ua in user_achs:
            a = ua.achievement
            ach_list.append({
                "key": a.key,
                "name": a.name,
                "description": a.description,
                "icon": a.icon,
                "awarded_at": ua.awarded_at.isoformat(),
            })

        recent_xp = (
            session.query(XPEvent)
            .filter_by(user_id=user_id)
            .order_by(XPEvent.created_at.desc())
            .limit(10)
            .all()
        )

        return {
            "xp": profile.xp_total,
            "level": level,
            "xp_into_level": xp_into,
            "xp_for_next_level": xp_needed,
            "streak_days": profile.current_streak_days,
            "longest_streak": profile.longest_streak_days,
            "coins": profile.coins,
            "achievements": ach_list,
            "recent_xp_events": [
                {"type": e.event_type, "amount": e.xp_awarded, "at": e.created_at.isoformat()}
                for e in recent_xp
            ],
        }

    if db is not None:
        return _get(db)
    with get_db() as session:
        return _get(session)
