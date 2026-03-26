"""
One-time migration: copy ro_leads.db data into the main owner_inbox.db.
Run once from the Owner Inbox directory.
"""
import sqlite3
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, 'ro_leads', 'ro_leads.db')
DST = os.path.join(BASE, 'instance', 'owner_inbox.db')

src = sqlite3.connect(SRC)
src.row_factory = sqlite3.Row
dst = sqlite3.connect(DST)
dst.execute("PRAGMA foreign_keys = ON")

# Ensure destination tables exist (init_db may not have run yet)
dst.executescript("""
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
        created_at TEXT DEFAULT (datetime('now'))
    );
""")

# Migrate prospects
prospects = src.execute("SELECT * FROM prospects").fetchall()
for p in prospects:
    dst.execute(
        """INSERT OR IGNORE INTO prospects
           (id, business_name, address, phone, website, industry, state, city,
            ro_products, suggested_contact_title, status, notes, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (p['id'], p['business_name'], p['address'], p['phone'], p['website'],
         p['industry'], p['state'], p['city'], p['ro_products'],
         p['suggested_contact_title'], p['status'], p['notes'],
         p['created_at'], p['updated_at'])
    )
print(f"Migrated {len(prospects)} prospects")

# Migrate contacts -> ro_contacts
contacts = src.execute("SELECT * FROM contacts").fetchall()
for c in contacts:
    dst.execute(
        """INSERT OR IGNORE INTO ro_contacts
           (id, prospect_id, name, title, email, phone, linkedin_url, notes, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (c['id'], c['prospect_id'], c['name'], c['title'], c['email'],
         c['phone'], c['linkedin_url'], c['notes'], c['created_at'])
    )
print(f"Migrated {len(contacts)} contacts")

dst.commit()
src.close()
dst.close()
print("Migration complete.")
