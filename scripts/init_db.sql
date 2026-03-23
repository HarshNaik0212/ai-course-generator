-- Extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- ═══════════════════════════════
-- USERS
-- ═══════════════════════════════
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email       TEXT UNIQUE NOT NULL,
    name        TEXT,
    skill_level TEXT CHECK (skill_level IN ('beginner','intermediate','advanced')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════
-- USER KNOWLEDGE STATE
-- ═══════════════════════════════
CREATE TABLE IF NOT EXISTS user_knowledge_state (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID REFERENCES users(id) ON DELETE CASCADE,
    concept          TEXT NOT NULL,
    confidence_score FLOAT DEFAULT 0.0,
    times_practiced  INT DEFAULT 0,
    last_error       TEXT,
    updated_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, concept)
);

-- ═══════════════════════════════
-- COURSES
-- ═══════════════════════════════
CREATE TABLE IF NOT EXISTS courses (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID REFERENCES users(id) ON DELETE CASCADE,
    topic          TEXT NOT NULL,
    duration_weeks INT,
    hours_per_day  INT,
    goals          TEXT[],
    status         TEXT DEFAULT 'active',
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS week_plans (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id    UUID REFERENCES courses(id) ON DELETE CASCADE,
    week_number  INT NOT NULL,
    theme        TEXT,
    objectives   TEXT[],
    is_completed BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS day_plans (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_plan_id UUID REFERENCES week_plans(id) ON DELETE CASCADE,
    day_number   INT NOT NULL,
    tasks        JSONB,
    is_completed BOOLEAN DEFAULT FALSE,
    content_completed BOOLEAN DEFAULT FALSE,   
    completed_at TIMESTAMPTZ
);

-- ═══════════════════════════════
-- KNOWLEDGE BASE (RAG)
-- ═══════════════════════════════
CREATE TABLE IF NOT EXISTS documents (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title      TEXT NOT NULL,
    doc_type   TEXT,
    topic      TEXT,
    metadata   JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID REFERENCES documents(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    chunk_index     INT,
    level           INT DEFAULT 0,
    parent_chunk_id UUID REFERENCES chunks(id),
    dense_embedding vector(384),
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Vector similarity index
CREATE INDEX IF NOT EXISTS chunks_hnsw
    ON chunks USING hnsw(dense_embedding vector_cosine_ops)
    WITH (m=16, ef_construction=64);

-- Full-text search index
CREATE INDEX IF NOT EXISTS chunks_fts
    ON chunks USING gin(to_tsvector('english', content));

-- ═══════════════════════════════
-- CONVERSATION HISTORY
-- ═══════════════════════════════
CREATE TABLE IF NOT EXISTS conversations (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id     UUID NOT NULL,
    role           TEXT CHECK (role IN ('user','assistant')),
    content        TEXT NOT NULL,
    embedding      vector(384),
    module_context TEXT,
    course_id      UUID REFERENCES courses(id),
    is_summarized  BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS conv_user_session
    ON conversations(user_id, session_id, created_at);

CREATE INDEX IF NOT EXISTS conv_hnsw
    ON conversations USING hnsw(embedding vector_cosine_ops);

-- ═══════════════════════════════
-- QUIZZES
-- ═══════════════════════════════
CREATE TABLE IF NOT EXISTS quiz_questions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    course_id      UUID REFERENCES courses(id) ON DELETE CASCADE,
    week_number    INT,                        
    day_number     INT,    
    question_text  TEXT NOT NULL,
    question_type  TEXT CHECK (question_type IN ('mcq','code','short_answer')),
    options        JSONB,
    correct_answer TEXT,
    explanation    TEXT,
    difficulty     INT CHECK (difficulty BETWEEN 1 AND 5),
    concept_tags   TEXT[]
);

CREATE TABLE IF NOT EXISTS quiz_attempts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    question_id  UUID REFERENCES quiz_questions(id),
    user_answer  TEXT,
    is_correct   BOOLEAN,
    attempted_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════
-- SEMANTIC CACHE
-- ═══════════════════════════════
CREATE TABLE IF NOT EXISTS query_cache (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    query_text      TEXT NOT NULL,
    query_embedding vector(384),
    response        TEXT NOT NULL,
    hit_count       INT DEFAULT 1,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS cache_hnsw
    ON query_cache USING hnsw(query_embedding vector_cosine_ops);

-- ═══════════════════════════════
-- CERTIFICATES
-- ═══════════════════════════════
CREATE TABLE IF NOT EXISTS certificates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    course_id       UUID REFERENCES courses(id) ON DELETE CASCADE,
    issued_at       TIMESTAMPTZ DEFAULT NOW(),
    quiz_score_avg  FLOAT,
    is_unlocked     BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, course_id)
);    