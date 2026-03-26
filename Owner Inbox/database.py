import sqlite3
from flask import g, current_app


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_type TEXT,
            description TEXT,
            tags TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            category TEXT,
            tags TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS pipeline_stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            stage_order INTEGER NOT NULL,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT,
            email TEXT,
            phone TEXT,
            company TEXT,
            role TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
            source TEXT,
            status TEXT DEFAULT 'new',
            value REAL,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
            lead_id INTEGER REFERENCES leads(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            stage TEXT,
            value REAL,
            close_date TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            priority TEXT DEFAULT 'medium',
            start_date TEXT,
            target_date TEXT,
            tags TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS project_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT,
            assigned_to TEXT,
            status TEXT DEFAULT 'todo',
            priority TEXT DEFAULT 'medium',
            due_date TEXT,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            skills TEXT,
            model TEXT,
            status TEXT DEFAULT 'idle',
            current_task TEXT,
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS prospects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_name TEXT NOT NULL,
            address TEXT,
            phone TEXT,
            website TEXT,
            industry TEXT,
            state TEXT,
            city TEXT,
            ro_products TEXT,
            suggested_contact_title TEXT,
            status TEXT DEFAULT 'new',
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS ro_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER REFERENCES prospects(id) ON DELETE CASCADE,
            name TEXT,
            title TEXT,
            email TEXT,
            phone TEXT,
            linkedin_url TEXT,
            notes TEXT,
            is_suggested INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            direction TEXT NOT NULL CHECK (direction IN ('in', 'out')),
            content TEXT NOT NULL,
            sender TEXT DEFAULT 'user',
            read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_chat_unread ON chat_messages(direction, read, created_at);
    """)

    # Seed pipeline_stages if empty
    count = db.execute("SELECT COUNT(*) FROM pipeline_stages").fetchone()[0]
    if count == 0:
        stages = [
            ('Prospecting', 1),
            ('Qualified', 2),
            ('Proposal', 3),
            ('Negotiation', 4),
            ('Closed Won', 5),
            ('Closed Lost', 6),
        ]
        db.executemany(
            "INSERT INTO pipeline_stages (name, stage_order) VALUES (?, ?)",
            stages
        )
    db.commit()

    # Migrate: add model column if missing
    agent_cols = [row[1] for row in db.execute("PRAGMA table_info(agents)").fetchall()]
    if 'model' not in agent_cols:
        db.execute("ALTER TABLE agents ADD COLUMN model TEXT")
        db.commit()

    # Seed agents if empty
    agent_count = db.execute("SELECT COUNT(*) FROM agents").fetchone()[0]
    if agent_count == 0:
        agents = [
            ('Ian', 'HR Agent', 'Hiring, agent onboarding, role definition', 'claude-sonnet-4-6', 'idle'),
            ('Sage', 'Senior Researcher', 'Market research, competitive analysis, role profiling', 'claude-sonnet-4-6', 'idle'),
            ('Maya', 'Full-Stack Developer', 'Python, Flask, SQLite, HTML/CSS, CRUD apps', 'claude-sonnet-4-6', 'idle'),
            ('Rex', 'Automation Engineer', 'Python scripting, scheduling, Discord API', 'claude-sonnet-4-6', 'idle'),
            ('Kai', 'Marketing Data Scraper', 'Web scraping, Apify, BeautifulSoup, SQLite, data pipelines', 'claude-sonnet-4-6', 'idle'),
        ]
        db.executemany(
            "INSERT INTO agents (name, role, skills, model, status) VALUES (?, ?, ?, ?, ?)",
            agents
        )
    db.commit()
