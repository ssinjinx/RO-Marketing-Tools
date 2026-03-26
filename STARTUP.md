# RO Marketing Tools — Session Startup Guide

## What This System Is

RO Marketing Tools is a business assistant suite built for Roberts Oxygen. It combines a Flask web dashboard (Owner Inbox) with a Discord monitoring bot, a prospect database, and an AI agent team. The owner interacts with the system through the web UI and Discord; the AI team handles research, development, scraping, and automation in the background.

---

## Starting the Apps

Run these commands to bring the system back online:

```bash
# Start the Owner Inbox web app (main business dashboard)
cd "/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox" && python3 app.py &

# Start Rex's DB monitor (checks DB every 10 min, posts updates to Discord #ro-sales-rep)
cd "/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox" && python3 monitor.py &

# Start the Team Inbox Watcher (monitors Team Inbox for new tasks, assigns to agents)
cd "/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox" && python3 team_inbox_watcher.py &
```

To confirm all are running:
```bash
ps aux | grep python3
```

---

## Accessing the Apps

| Access | URL | PIN |
|--------|-----|-----|
| Local | http://localhost:5000 | 6911 |
| Remote (Cloudflare) | https://ro-inbox.siliconsoul.cloud | 6911 |

---

## The AI Team

| Agent | Role | What They Do |
|-------|------|--------------|
| **Sage** | Senior Researcher | Researches real-world expertise and requirements before new agents are hired |
| **Ian** | HR Agent | Hires new agents; builds their identity, name, and persona based on Sage's research |
| **Maya** | Full-Stack Developer | Builds and maintains the Flask web apps and UI features |
| **Rex** | Automation Engineer | Scheduled scripts and the Discord monitor |
| **Kai** | Marketing Data Scraper | Apify scraping pipelines and the prospect database |

---

## Workflow: Project → Team Inbox → Agent

1. **Create a Project** via the Owner Inbox web UI (`/projects/new`)
2. **Auto-generated Task File** appears in `Team Inbox/` with:
   - Project name, description, priority
   - Suggested agent based on task type
   - Task checklist for the agent
3. **Team Inbox Watcher** detects the new file and:
   - Parses the project details
   - Updates the suggested agent's status to `working`
   - Sets their `current_task` to the project summary
   - Sends Discord notification (if configured)

### Agent Task Mapping

| Task Type | Assigned To |
|-----------|-------------|
| UI/development/Flask/web | Maya |
| Research/analysis/market | Sage |
| Scraping/data/Apify/pipeline | Kai |
| Automation/script/monitor/Discord | Rex |
| Hiring/onboarding/agent/HR | Ian |

---

## Current Open Projects

### Project #2 — Marketing Scrap Information Database
- **Status:** Active | **Priority:** High
- **Summary:** Research Roberts Oxygen (products, services, service areas), then build a scraping tool that pulls prospects by facility area (dropdown), and creates profile cards in the DB for each prospect — including business breakdown, likely products needed, key contacts, and Roberts Oxygen relevance.
- **Owner:** Kai (scraping) with support from Maya (UI) and Sage (initial research)

### Project #3 — Team Table Widget
- **Status:** Active | **Priority:** Medium
- **Summary:** Add a UI panel to the Owner Inbox website showing each agent — their name, status (working/idle), current task, skills, LLM model in use, and a direct task-send button.
- **Owner:** Maya (UI build)

---

## Key File Locations

| What | Path |
|------|------|
| Web app | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/app.py` |
| DB monitor | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/monitor.py` |
| Team Inbox Watcher | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/team_inbox_watcher.py` |
| Main database | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/instance/owner_inbox.db` |
| Business DB | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/business.db` |
| DB schema/models | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/database.py` |
| Templates (HTML) | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/templates/` |
| Static assets | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/static/` |
| Reports output | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/reports/` |
| Project CLAUDE.md | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/.claude/CLAUDE.md` |
| Team Inbox | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Team Inbox/` |
| Owner Inbox dir | `/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/` |
