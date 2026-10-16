-- ==============================================================================
-- RepoCompass — Complete PostgreSQL Schema for Supabase
-- Run this script in the Supabase SQL Editor (Dashboard -> SQL Editor -> New Query)
-- ==============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table
CREATE TABLE IF NOT EXISTS public.users (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT,
    display_name TEXT NOT NULL,
    avatar_url TEXT,
    github_username TEXT,
    github_access_token_encrypted TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_users_email ON public.users (email);

-- 2. Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id TEXT UNIQUE NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    bio TEXT,
    experience_level TEXT DEFAULT 'beginner',
    years_of_experience INTEGER DEFAULT 1,
    programming_languages JSONB DEFAULT '[]'::jsonb,
    interests JSONB DEFAULT '[]'::jsonb,
    contribution_goals JSONB DEFAULT '[]'::jsonb,
    preferred_issue_types JSONB DEFAULT '[]'::jsonb,
    open_source_contributions_count INTEGER DEFAULT 0,
    comfortable_with_testing BOOLEAN DEFAULT FALSE,
    comfortable_with_git BOOLEAN DEFAULT TRUE,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    xp_total INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    coins INTEGER DEFAULT 0,
    current_streak_days INTEGER DEFAULT 0,
    longest_streak_days INTEGER DEFAULT 0,
    last_activity_date TEXT,
    profile_public BOOLEAN DEFAULT TRUE,
    leaderboard_visible BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Repositories Table
CREATE TABLE IF NOT EXISTS public.repositories (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    owner TEXT NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    url TEXT NOT NULL,
    description TEXT,
    primary_language TEXT,
    topics JSONB DEFAULT '[]'::jsonb,
    stars INTEGER DEFAULT 0,
    open_issues_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_analyzed_at TIMESTAMPTZ,
    analysis_status TEXT DEFAULT 'pending',
    CONSTRAINT uq_repo_owner_name UNIQUE (owner, name)
);

CREATE INDEX IF NOT EXISTS idx_repositories_full_name ON public.repositories (full_name);

-- 4. Repository Snapshots Table
CREATE TABLE IF NOT EXISTS public.repository_snapshots (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    repository_id TEXT NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    sha TEXT,
    raw_data JSONB DEFAULT '{}'::jsonb,
    directory_tree JSONB DEFAULT '[]'::jsonb,
    readme_content TEXT,
    contributing_content TEXT,
    dependency_files JSONB DEFAULT '{}'::jsonb,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- 5. Issues Table
CREATE TABLE IF NOT EXISTS public.issues (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    repository_id TEXT NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    github_id BIGINT NOT NULL,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    state TEXT DEFAULT 'open',
    labels JSONB DEFAULT '[]'::jsonb,
    assignees JSONB DEFAULT '[]'::jsonb,
    author TEXT,
    html_url TEXT NOT NULL,
    comments_count INTEGER DEFAULT 0,
    created_at_gh TIMESTAMPTZ,
    updated_at_gh TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_issue_repo_number UNIQUE (repository_id, number)
);

CREATE INDEX IF NOT EXISTS ix_issue_repo_state ON public.issues (repository_id, state);

-- 6. Issue Scores Table
CREATE TABLE IF NOT EXISTS public.issue_scores (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    issue_id TEXT UNIQUE NOT NULL REFERENCES public.issues(id) ON DELETE CASCADE,
    total_score DOUBLE PRECISION DEFAULT 0.0,
    difficulty_estimate TEXT,
    signals JSONB DEFAULT '{}'::jsonb,
    explanation TEXT,
    computed_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Guides Table
CREATE TABLE IF NOT EXISTS public.guides (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    repository_id TEXT NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    snapshot_id TEXT REFERENCES public.repository_snapshots(id),
    model_name TEXT,
    content JSONB DEFAULT '{}'::jsonb,
    status TEXT DEFAULT 'generating',
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Practice Sessions Table
CREATE TABLE IF NOT EXISTS public.practice_sessions (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    issue_id TEXT REFERENCES public.issues(id),
    repository_id TEXT NOT NULL REFERENCES public.repositories(id),
    status TEXT DEFAULT 'active',
    patch_draft TEXT,
    ai_review TEXT,
    hint_level_reached INTEGER DEFAULT 0,
    hints_used JSONB DEFAULT '[]'::jsonb,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- 9. XP Events Table
CREATE TABLE IF NOT EXISTS public.xp_events (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    xp_awarded INTEGER NOT NULL,
    idempotency_key TEXT UNIQUE NOT NULL,
    event_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Achievements & User Achievements
CREATE TABLE IF NOT EXISTS public.achievements (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    icon TEXT DEFAULT '🏆',
    xp_reward INTEGER DEFAULT 0,
    condition_type TEXT,
    condition_value JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.user_achievements (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    achievement_id TEXT NOT NULL REFERENCES public.achievements(id),
    awarded_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_user_achievement UNIQUE (user_id, achievement_id)
);

-- 11. User Skills
CREATE TABLE IF NOT EXISTS public.user_skills (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    evidence_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    CONSTRAINT uq_user_skill UNIQUE (user_id, skill_name)
);

-- 12. Activity Events Table
CREATE TABLE IF NOT EXISTS public.activity_events (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    description TEXT,
    event_metadata JSONB DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

-- 13. Maintainer Drafts Table
CREATE TABLE IF NOT EXISTS public.maintainer_drafts (
    id TEXT PRIMARY KEY DEFAULT uuid_generate_v4()::text,
    user_id TEXT NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
    repository_id TEXT NOT NULL REFERENCES public.repositories(id),
    issue_id TEXT REFERENCES public.issues(id),
    draft_type TEXT NOT NULL,
    title TEXT,
    content TEXT,
    rationale TEXT,
    status TEXT DEFAULT 'draft',
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Success message
SELECT 'RepoCompass schema created successfully!' AS status;
