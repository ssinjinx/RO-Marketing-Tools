# RO Marketing Tools

A business assistant web application built for Roberts Oxygen — managing prospects, CRM, projects, and an AI agent team from a single local dashboard.

---

## Overview

RO Marketing Tools is a Flask-based business management system that combines:

- **Owner Inbox Dashboard** — Central hub for managing everything
- **CRM** — Contacts, leads, deals, and pipeline
- **Prospect Database** — Roberts Oxygen leads with cold email generation
- **Projects & Tasks** — Assign work to AI agents via a Team Inbox
- **Knowledge Base & File Catalog** — Business documentation
- **Live Monitor** — Discord alerts for open projects and tasks
- **AI Agent Team** — 5 specialized agents (Sage, Ian, Maya, Rex, Kai)

---

## Access

| Mode | URL | PIN |
|------|-----|-----|
| Local | `http://localhost:5000` | `6911` |
| Remote (Cloudflare Tunnel) | `https://ro-inbox.siliconsoul.cloud` | `6911` |

---

## Project Structure

```
RO-Marketing-Tools/
├── Owner Inbox/                  # Main Flask web application
│   ├── app.py                    # Core app — all routes (54+)
│   ├── database.py               # SQLite schema and initialization
│   ├── monitor.py                # Background monitor — posts to Discord every 10 min
│   ├── team_inbox_watcher.py     # Watches Team Inbox for new task files
│   ├── chat_bridge.py            # WebSocket chat orchestration
│   ├── requirements.txt          # Main app dependencies
│   ├── monitor_requirements.txt  # Monitor dependencies
│   ├── .env                      # API keys (NEVER commit — gitignored)
│   ├── instance/
│   │   ├── owner_inbox.db        # Main SQLite database (96KB)
│   │   └── business.db           # Reserved for future analytics
│   ├── static/
│   │   └── style.css             # Responsive CSS design system
│   ├── templates/                # 31 Jinja2 HTML templates
│   │   ├── base.html             # Layout with nav and hamburger menu
│   │   ├── index.html            # Dashboard
│   │   ├── lock.html             # PIN login page
│   │   ├── crm/                  # Contacts, leads, deals, pipeline
│   │   ├── file_catalog/         # File tracking
│   │   ├── knowledge_base/       # Business docs
│   │   ├── projects/             # Projects and tasks
│   │   └── ro/                   # RO prospect database UI
│   ├── ro_leads/                 # Secondary prospect scraping app
│   │   ├── app.py
│   │   ├── database.py
│   │   ├── batch_search.py
│   │   ├── requirements.txt
│   │   └── ro_leads.db           # Prospect scraping database
│   └── reports/                  # Timestamped monitor report files
│
├── Team Inbox/                   # Owner drops task files here
│   └── README.md
│
├── Team/                         # AI agent profile definitions
│   ├── Sage.md
│   ├── Ian.md
│   ├── Dev_Maya.md
│   ├── Automation_Rex.md
│   └── Scraper_Kai.md
│
├── .claude/
│   └── CLAUDE.md                 # Orchestrator instructions for Claude
│
└── STARTUP.md                    # Quick-start reference
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/ssinjin/RO-Marketing-Tools.git
cd RO-Marketing-Tools
```

### 2. Install dependencies

```bash
cd "Owner Inbox"

# Main app
pip install flask flask-socketio anthropic requests beautifulsoup4 apify-client

# Or install from requirements files
pip install -r requirements.txt
pip install -r monitor_requirements.txt
pip install -r ro_leads/requirements.txt
```

### 3. Create the `.env` file

Create `Owner Inbox/.env` with the following:

```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_CHANNEL_ID=your_discord_channel_id_here
```

> **Never commit `.env`.** It is gitignored.

### 4. Initialize the database

The database is created and seeded automatically on first run via `database.py`. It creates all tables and seeds:
- 6 CRM pipeline stages (Prospecting → Closed Won/Lost)
- 5 AI agents (Ian, Sage, Maya, Rex, Kai)

### 5. Start the app

```bash
# Terminal 1 — Web app
cd "Owner Inbox" && python3 app.py

# Terminal 2 — Background monitor (optional)
cd "Owner Inbox" && python3 monitor.py

# Terminal 3 — Team Inbox watcher (optional)
cd "Owner Inbox" && python3 team_inbox_watcher.py
```

Open `http://localhost:5000` and enter PIN `6911`.

---

## Configuration

### App Config (hardcoded in `app.py`)

| Setting | Value | Description |
|---------|-------|-------------|
| PIN | `6911` | Dashboard access PIN |
| Flask secret key | `fallback-dev-key` | Override via `SECRET_KEY` env var |
| Database path | `instance/owner_inbox.db` | SQLite main database |
| Monitor interval | `600` seconds | How often monitor checks for changes |
| Watcher poll interval | `2` seconds | How often watcher scans Team Inbox |

### Environment Variables (`.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key for cold email generation and chat |
| `DISCORD_BOT_TOKEN` | Yes (for monitor) | Discord bot token for report posting |
| `DISCORD_CHANNEL_ID` | Yes (for monitor) | Target Discord channel for reports |

### Remote Access (Cloudflare Tunnel)

The app is exposed via a Cloudflare tunnel. To reconfigure, update the tunnel target to point to `http://localhost:5000`.

---

## Database

### Main Database: `instance/owner_inbox.db`

| Table | Description |
|-------|-------------|
| `files` | File catalog — tracked business documents |
| `articles` | Knowledge base articles |
| `pipeline_stages` | CRM pipeline stages (seeded on init) |
| `contacts` | CRM contacts |
| `leads` | CRM leads (linked to contacts) |
| `deals` | CRM deals (linked to contacts and leads) |
| `projects` | Business projects |
| `project_tasks` | Tasks within projects |
| `agents` | AI team members (seeded on init) |
| `prospects` | Roberts Oxygen prospect companies |
| `ro_contacts` | Contacts at prospect companies |
| `chat_messages` | Chat history between owner and orchestrator |

### Secondary Database: `ro_leads/ro_leads.db`

Used by the `ro_leads/` sub-app for Apify scraping results and prospect enrichment.

### Migrations

Migration scripts are in `migrations/`. Run manually as needed:

```bash
cd "Owner Inbox"
python3 migrations/<migration_file>.py
```

---

## Routes

### Core
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Dashboard |
| GET/POST | `/lock` | PIN login page |
| POST | `/unlock` | PIN validation |

### File Catalog
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/files` | List all files |
| GET/POST | `/files/new` | Add file |
| GET | `/files/<id>` | View file |
| GET/POST | `/files/<id>/edit` | Edit file |
| POST | `/files/<id>/delete` | Delete file |

### Knowledge Base
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/kb` | List articles |
| GET/POST | `/kb/new` | Create article |
| GET | `/kb/<id>` | View article |
| GET/POST | `/kb/<id>/edit` | Edit article |
| POST | `/kb/<id>/delete` | Delete article |

### CRM
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/crm/contacts` | List contacts |
| GET/POST | `/crm/contacts/new` | Add contact |
| GET | `/crm/contacts/<id>` | View contact |
| GET/POST | `/crm/contacts/<id>/edit` | Edit contact |
| GET | `/crm/leads` | List leads |
| GET/POST | `/crm/leads/new` | Add lead |
| GET | `/crm/deals` | List deals |
| GET/POST | `/crm/deals/new` | Add deal |
| GET | `/crm/pipeline` | Pipeline kanban view |

### Projects
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/projects` | List projects |
| GET/POST | `/projects/new` | Create project |
| GET | `/projects/<id>` | View project |
| GET/POST | `/projects/<id>/edit` | Edit project |
| POST | `/projects/<id>/delete` | Delete project |
| GET/POST | `/projects/<id>/tasks/new` | Add task |

### AI Agents
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/agents/<id>/task` | Assign task to agent |
| POST | `/agents/<id>/status` | Update agent status |

### RO Prospects
| Method | Route | Description |
|--------|-------|-------------|
| GET | `/ro/info` | Roberts Oxygen company info |
| GET/POST | `/ro/search` | Search for prospects (Apify) |
| POST | `/ro/search/save` | Save search result |
| GET | `/ro/profiles` | List all prospects |
| GET/POST | `/ro/profiles/add` | Add prospect manually |
| GET | `/ro/profiles/<id>` | View prospect |
| GET | `/ro/contacts` | List all contacts |
| GET/POST | `/ro/contacts/add` | Add contact |
| GET | `/ro/pipeline` | Prospect pipeline view |
| POST | `/ro/pipeline/move/<id>` | Move prospect to new stage |
| POST | `/ro/profiles/<id>/find-contacts` | Scrape contacts for prospect |
| POST | `/ro/contacts/<id>/draft-email` | Generate cold outreach email via Claude |

### Chat
| Method | Route | Description |
|--------|-------|-------------|
| POST | `/chat/send` | Send message to orchestrator |
| GET | `/chat/poll` | Poll for orchestrator responses |
| GET | `/chat/history` | Get last 50 chat messages |

---

## AI Agent Team

The app manages 5 AI agents, each with a defined role and persona:

| Agent | Role | Responsibilities |
|-------|------|-----------------|
| **Sage** | Senior Researcher | Research roles, market intel, scoping work before execution |
| **Ian** | HR Agent | Hiring new agents based on Sage's research |
| **Maya** | Full-Stack Developer | Flask app, templates, database, CRUD features |
| **Rex** | Automation Engineer | Scheduled scripts, Discord monitor, background automation |
| **Kai** | Marketing Data Scraper | Apify pipelines, prospect database, data workflows |

All agents run on `claude-sonnet-4-6`.

### Workflow

```
Team Inbox (owner drops task .md file)
    → team_inbox_watcher.py detects file
        → Orchestrator reads and routes to agent
            → Agent executes task
                → Owner Inbox (results delivered)
```

### Assigning Tasks

Drop a `.md` file in the `Team Inbox/` directory:

```markdown
# Task Title

**Suggested Agent:** Maya
**Priority:** high

## Description

What needs to be built or done...
```

The watcher auto-detects the file, updates agent status in the DB, and posts a Discord alert.

---

## Background Services

### `monitor.py`

Runs every 10 minutes. Queries the database for open projects and tasks, posts a summary report to Discord, saves a timestamped report file to `reports/`, and alerts on newly detected items.

```bash
python3 monitor.py          # Continuous (default)
python3 monitor.py --once   # Run once and exit
```

**Tracks state in:** `monitor_state.json`
**Reports saved to:** `reports/report_YYYYMMDD_HHMMSS.txt`

### `team_inbox_watcher.py`

Polls `Team Inbox/` every 2 seconds for new `.md` files. Parses task metadata, updates agent status in DB, and sends Discord notification on new assignments.

---

## Design System

All styles are in `static/style.css`. Key design decisions:

| Token | Value | Use |
|-------|-------|-----|
| Primary green | `#1a5c35` | Brand color, buttons, nav accents |
| Accent gold | `#e8a020` | Highlights, badges |
| Dark nav | `#081120` | Navigation bar background |
| Card radius | `12px` | Consistent card rounding |

**Mobile:** Fully responsive via flexbox and media queries. Hamburger menu on mobile via `base.html`.

---

## Security Notes

- The PIN (`6911`) is hardcoded in `app.py`. Change it before deploying publicly.
- `.env` is gitignored — never commit API keys.
- No user accounts — single-owner PIN access only.
- The Flask secret key falls back to a default dev value. Set `SECRET_KEY` in `.env` for production.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Web framework | Flask 3.0 + Flask-SocketIO |
| Database | SQLite via `sqlite3` |
| Frontend | Jinja2 templates + custom CSS |
| AI | Anthropic Claude API (`claude-sonnet-4-6`) |
| Scraping | Apify client + BeautifulSoup |
| Notifications | Discord Bot API |
| Remote access | Cloudflare Tunnel |
| Orchestration | Claude Code (OpenClaw) |
