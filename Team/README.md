# AI Team

This folder contains a profile for every member of the AI team.

Each member has a **Name**, **Identity**, and **Persona** and owns a specific area of responsibility.

---

## Current Roster

| Name | Role | Responsibility |
|------|------|---------------|
| [Ian](Ian.md) | HR Agent | Hires new agents based on needed expertise |
| [Sage](Sage.md) | Senior Researcher | Researches real-world skills required for a given role |
| [Maya](Dev_Maya.md) | Full-Stack Developer | Builds and maintains the local Flask business management system |
| [Rex](Automation_Rex.md) | Automation Engineer | Builds scheduled monitor scripts, local AI integrations, and system reporting pipelines |
| [Kai](Scraper_Kai.md) | Marketing Data Scraper | Scrapes marketing intelligence from the web and manages the Marketing Scrap Information Database |

---

## How the Team Works

1. The **orchestrator** (Claude) receives a task or identifies a need.
2. The orchestrator **never does the work** — it routes to the right team member.
3. For new roles: **Sage researches** → **Ian hires** → new agent joins the team.
4. For existing tasks: orchestrator routes directly to the relevant specialist.

---

## Agent File Format

Each agent file contains:
- **Identity** — who they are
- **Persona** — how they think and behave
- **Role** — their title
- **Responsibilities** — what they own
- **How It Works** — their place in the workflow
