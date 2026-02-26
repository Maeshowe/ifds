"""Database schema definitions for CONDUCTOR memory."""

SCHEMA_VERSION = 4

TABLES_SQL = """
-- Sessions: munkamenet-nyilvántartás
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    summary TEXT,
    context TEXT
);

-- Decisions: aktív döntések nyilvántartása
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    alternatives TEXT,
    rationale TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    tags TEXT
);

-- Tasks: feladatok követése
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    session_id INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- Learnings: tanulságok, felfedezések, korrekciók
CREATE TABLE IF NOT EXISTS learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

FTS_SQL = """
-- FTS5 virtual tables for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS sessions_fts USING fts5(
    summary, context, content=sessions, content_rowid=id
);

CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
    title, description, rationale, content=decisions, content_rowid=id
);

CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
    title, description, content=tasks, content_rowid=id
);

CREATE VIRTUAL TABLE IF NOT EXISTS learnings_fts USING fts5(
    content, content=learnings, content_rowid=id
);
"""

# Triggers to keep FTS indexes in sync
FTS_TRIGGERS_SQL = """
-- Sessions FTS sync
CREATE TRIGGER IF NOT EXISTS sessions_ai AFTER INSERT ON sessions BEGIN
    INSERT INTO sessions_fts(rowid, summary, context)
    VALUES (new.id, new.summary, new.context);
END;
CREATE TRIGGER IF NOT EXISTS sessions_au AFTER UPDATE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, summary, context)
    VALUES ('delete', old.id, old.summary, old.context);
    INSERT INTO sessions_fts(rowid, summary, context)
    VALUES (new.id, new.summary, new.context);
END;
CREATE TRIGGER IF NOT EXISTS sessions_ad AFTER DELETE ON sessions BEGIN
    INSERT INTO sessions_fts(sessions_fts, rowid, summary, context)
    VALUES ('delete', old.id, old.summary, old.context);
END;

-- Decisions FTS sync
CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
    INSERT INTO decisions_fts(rowid, title, description, rationale)
    VALUES (new.id, new.title, new.description, new.rationale);
END;
CREATE TRIGGER IF NOT EXISTS decisions_au AFTER UPDATE ON decisions BEGIN
    INSERT INTO decisions_fts(decisions_fts, rowid, title, description, rationale)
    VALUES ('delete', old.id, old.title, old.description, old.rationale);
    INSERT INTO decisions_fts(rowid, title, description, rationale)
    VALUES (new.id, new.title, new.description, new.rationale);
END;
CREATE TRIGGER IF NOT EXISTS decisions_ad AFTER DELETE ON decisions BEGIN
    INSERT INTO decisions_fts(decisions_fts, rowid, title, description, rationale)
    VALUES ('delete', old.id, old.title, old.description, old.rationale);
END;

-- Tasks FTS sync
CREATE TRIGGER IF NOT EXISTS tasks_ai AFTER INSERT ON tasks BEGIN
    INSERT INTO tasks_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;
CREATE TRIGGER IF NOT EXISTS tasks_au AFTER UPDATE ON tasks BEGIN
    INSERT INTO tasks_fts(tasks_fts, rowid, title, description)
    VALUES ('delete', old.id, old.title, old.description);
    INSERT INTO tasks_fts(rowid, title, description)
    VALUES (new.id, new.title, new.description);
END;
CREATE TRIGGER IF NOT EXISTS tasks_ad AFTER DELETE ON tasks BEGIN
    INSERT INTO tasks_fts(tasks_fts, rowid, title, description)
    VALUES ('delete', old.id, old.title, old.description);
END;

-- Learnings FTS sync
CREATE TRIGGER IF NOT EXISTS learnings_ai AFTER INSERT ON learnings BEGIN
    INSERT INTO learnings_fts(rowid, content)
    VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS learnings_au AFTER UPDATE ON learnings BEGIN
    INSERT INTO learnings_fts(learnings_fts, rowid, content)
    VALUES ('delete', old.id, old.content);
    INSERT INTO learnings_fts(rowid, content)
    VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS learnings_ad AFTER DELETE ON learnings BEGIN
    INSERT INTO learnings_fts(learnings_fts, rowid, content)
    VALUES ('delete', old.id, old.content);
END;
"""

# --- Central DB schema (cross-project, ~/.conductor/central.db) ---

CENTRAL_TABLES_SQL = """
-- Projects: registered CONDUCTOR projects
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    path TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_accessed TEXT
);

-- Cross-project decisions
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    alternatives TEXT,
    rationale TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    tags TEXT,
    source_project TEXT
);

-- Cross-project learnings
CREATE TABLE IF NOT EXISTS learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    content TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT,
    source_project TEXT
);

-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CENTRAL_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
    title, description, rationale, content=decisions, content_rowid=id
);

CREATE VIRTUAL TABLE IF NOT EXISTS learnings_fts USING fts5(
    content, content=learnings, content_rowid=id
);
"""

CENTRAL_FTS_TRIGGERS_SQL = """
-- Decisions FTS sync
CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
    INSERT INTO decisions_fts(rowid, title, description, rationale)
    VALUES (new.id, new.title, new.description, new.rationale);
END;
CREATE TRIGGER IF NOT EXISTS decisions_au AFTER UPDATE ON decisions BEGIN
    INSERT INTO decisions_fts(decisions_fts, rowid, title, description, rationale)
    VALUES ('delete', old.id, old.title, old.description, old.rationale);
    INSERT INTO decisions_fts(rowid, title, description, rationale)
    VALUES (new.id, new.title, new.description, new.rationale);
END;
CREATE TRIGGER IF NOT EXISTS decisions_ad AFTER DELETE ON decisions BEGIN
    INSERT INTO decisions_fts(decisions_fts, rowid, title, description, rationale)
    VALUES ('delete', old.id, old.title, old.description, old.rationale);
END;

-- Learnings FTS sync
CREATE TRIGGER IF NOT EXISTS learnings_ai AFTER INSERT ON learnings BEGIN
    INSERT INTO learnings_fts(rowid, content)
    VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS learnings_au AFTER UPDATE ON learnings BEGIN
    INSERT INTO learnings_fts(learnings_fts, rowid, content)
    VALUES ('delete', old.id, old.content);
    INSERT INTO learnings_fts(rowid, content)
    VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS learnings_ad AFTER DELETE ON learnings BEGIN
    INSERT INTO learnings_fts(learnings_fts, rowid, content)
    VALUES ('delete', old.id, old.content);
END;
"""

# --- Briefs table (project DB, for BA Bridge) ---

BRIEFS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    title TEXT NOT NULL,
    raw_idea TEXT NOT NULL,
    problem TEXT,
    target_user TEXT,
    scope_essential TEXT,
    scope_nice_to_have TEXT,
    scope_out TEXT,
    constraints TEXT,
    first_version TEXT,
    brief_text TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    session_id INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""

BRIEFS_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS briefs_fts USING fts5(
    title, raw_idea, problem, brief_text, content=briefs, content_rowid=id
);
"""

BRIEFS_FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS briefs_ai AFTER INSERT ON briefs BEGIN
    INSERT INTO briefs_fts(rowid, title, raw_idea, problem, brief_text)
    VALUES (new.id, new.title, new.raw_idea, new.problem, new.brief_text);
END;
CREATE TRIGGER IF NOT EXISTS briefs_au AFTER UPDATE ON briefs BEGIN
    INSERT INTO briefs_fts(briefs_fts, rowid, title, raw_idea, problem, brief_text)
    VALUES ('delete', old.id, old.title, old.raw_idea, old.problem, old.brief_text);
    INSERT INTO briefs_fts(rowid, title, raw_idea, problem, brief_text)
    VALUES (new.id, new.title, new.raw_idea, new.problem, new.brief_text);
END;
CREATE TRIGGER IF NOT EXISTS briefs_ad AFTER DELETE ON briefs BEGIN
    INSERT INTO briefs_fts(briefs_fts, rowid, title, raw_idea, problem, brief_text)
    VALUES ('delete', old.id, old.title, old.raw_idea, old.problem, old.brief_text);
END;
"""

# --- Build Plans table (project DB, for Technical Layer) ---

BUILD_PLANS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS build_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    brief_id INTEGER,
    title TEXT NOT NULL,
    description TEXT,
    approach TEXT,
    steps TEXT,
    files_to_create TEXT,
    files_to_modify TEXT,
    acceptance_criteria TEXT,
    estimated_complexity TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    session_id INTEGER,
    FOREIGN KEY (brief_id) REFERENCES briefs(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""

BUILD_PLANS_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS build_plans_fts USING fts5(
    title, description, approach, content=build_plans, content_rowid=id
);
"""

BUILD_PLANS_FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS build_plans_ai AFTER INSERT ON build_plans BEGIN
    INSERT INTO build_plans_fts(rowid, title, description, approach)
    VALUES (new.id, new.title, new.description, new.approach);
END;
CREATE TRIGGER IF NOT EXISTS build_plans_au AFTER UPDATE ON build_plans BEGIN
    INSERT INTO build_plans_fts(build_plans_fts, rowid, title, description, approach)
    VALUES ('delete', old.id, old.title, old.description, old.approach);
    INSERT INTO build_plans_fts(rowid, title, description, approach)
    VALUES (new.id, new.title, new.description, new.approach);
END;
CREATE TRIGGER IF NOT EXISTS build_plans_ad AFTER DELETE ON build_plans BEGIN
    INSERT INTO build_plans_fts(build_plans_fts, rowid, title, description, approach)
    VALUES ('delete', old.id, old.title, old.description, old.approach);
END;
"""

# --- Reviews table (project DB, for Technical Layer) ---

REVIEWS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    build_plan_id INTEGER,
    brief_id INTEGER,
    review_type TEXT NOT NULL DEFAULT 'code',
    scope TEXT,
    findings TEXT,
    verdict TEXT NOT NULL DEFAULT 'pending',
    summary TEXT,
    session_id INTEGER,
    FOREIGN KEY (build_plan_id) REFERENCES build_plans(id),
    FOREIGN KEY (brief_id) REFERENCES briefs(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""

REVIEWS_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS reviews_fts USING fts5(
    scope, summary, content=reviews, content_rowid=id
);
"""

REVIEWS_FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS reviews_ai AFTER INSERT ON reviews BEGIN
    INSERT INTO reviews_fts(rowid, scope, summary)
    VALUES (new.id, new.scope, new.summary);
END;
CREATE TRIGGER IF NOT EXISTS reviews_au AFTER UPDATE ON reviews BEGIN
    INSERT INTO reviews_fts(reviews_fts, rowid, scope, summary)
    VALUES ('delete', old.id, old.scope, old.summary);
    INSERT INTO reviews_fts(rowid, scope, summary)
    VALUES (new.id, new.scope, new.summary);
END;
CREATE TRIGGER IF NOT EXISTS reviews_ad AFTER DELETE ON reviews BEGIN
    INSERT INTO reviews_fts(reviews_fts, rowid, scope, summary)
    VALUES ('delete', old.id, old.scope, old.summary);
END;
"""

# --- Strategy Analyses table (project DB, for Strategy Layer) ---

STRATEGY_ANALYSES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS strategy_analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    title TEXT NOT NULL,
    input_text TEXT,
    findings TEXT,
    recommendation TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    session_id INTEGER,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""

STRATEGY_ANALYSES_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS strategy_analyses_fts USING fts5(
    title, input_text, recommendation, content=strategy_analyses, content_rowid=id
);
"""

STRATEGY_ANALYSES_FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS strategy_analyses_ai AFTER INSERT ON strategy_analyses BEGIN
    INSERT INTO strategy_analyses_fts(rowid, title, input_text, recommendation)
    VALUES (new.id, new.title, new.input_text, new.recommendation);
END;
CREATE TRIGGER IF NOT EXISTS strategy_analyses_au AFTER UPDATE ON strategy_analyses BEGIN
    INSERT INTO strategy_analyses_fts(strategy_analyses_fts, rowid, title, input_text, recommendation)
    VALUES ('delete', old.id, old.title, old.input_text, old.recommendation);
    INSERT INTO strategy_analyses_fts(rowid, title, input_text, recommendation)
    VALUES (new.id, new.title, new.input_text, new.recommendation);
END;
CREATE TRIGGER IF NOT EXISTS strategy_analyses_ad AFTER DELETE ON strategy_analyses BEGIN
    INSERT INTO strategy_analyses_fts(strategy_analyses_fts, rowid, title, input_text, recommendation)
    VALUES ('delete', old.id, old.title, old.input_text, old.recommendation);
END;
"""

# --- Test Runs table (project DB, for /test command) ---

TEST_RUNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS test_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    build_plan_id INTEGER,
    brief_id INTEGER,
    test_command TEXT NOT NULL,
    total_tests INTEGER,
    passed INTEGER,
    failed INTEGER,
    errors INTEGER,
    skipped INTEGER,
    duration_seconds REAL,
    output_summary TEXT,
    status TEXT NOT NULL DEFAULT 'passed',
    session_id INTEGER,
    FOREIGN KEY (build_plan_id) REFERENCES build_plans(id),
    FOREIGN KEY (brief_id) REFERENCES briefs(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""

TEST_RUNS_FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS test_runs_fts USING fts5(
    output_summary, test_command, content=test_runs, content_rowid=id
);
"""

TEST_RUNS_FTS_TRIGGERS_SQL = """
CREATE TRIGGER IF NOT EXISTS test_runs_ai AFTER INSERT ON test_runs BEGIN
    INSERT INTO test_runs_fts(rowid, output_summary, test_command)
    VALUES (new.id, new.output_summary, new.test_command);
END;
CREATE TRIGGER IF NOT EXISTS test_runs_au AFTER UPDATE ON test_runs BEGIN
    INSERT INTO test_runs_fts(test_runs_fts, rowid, output_summary, test_command)
    VALUES ('delete', old.id, old.output_summary, old.test_command);
    INSERT INTO test_runs_fts(rowid, output_summary, test_command)
    VALUES (new.id, new.output_summary, new.test_command);
END;
CREATE TRIGGER IF NOT EXISTS test_runs_ad AFTER DELETE ON test_runs BEGIN
    INSERT INTO test_runs_fts(test_runs_fts, rowid, output_summary, test_command)
    VALUES ('delete', old.id, old.output_summary, old.test_command);
END;
"""
