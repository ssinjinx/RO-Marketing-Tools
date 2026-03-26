import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "ro_leads.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
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

        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prospect_id INTEGER REFERENCES prospects(id) ON DELETE CASCADE,
            name TEXT,
            title TEXT,
            email TEXT,
            phone TEXT,
            linkedin_url TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()
