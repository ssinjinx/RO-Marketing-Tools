#!/usr/bin/env python3
"""
monitor.py — Scheduled monitor for open projects and tasks.
Queries SQLite DB every 10 minutes, summarizes with Ollama, posts to Discord,
and saves a timestamped report file.

Usage:
    python3 monitor.py          # run in loop (every 10 min)
    python3 monitor.py --once   # single run, then exit
"""

import sqlite3
import requests
import time
import datetime
import os
import sys
import json


def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())


load_env()

# --- Configuration -----------------------------------------------------------

DB_PATH = "/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/instance/owner_inbox.db"
REPORTS_DIR = "/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/reports"
STATE_FILE = "/home/ssinjin/.openclaw/workspace/RO-Marketing-Tools/Owner Inbox/monitor_state.json"
DISCORD_API_URL = "https://discord.com/api/v10/channels/{channel_id}/messages"
ORCHESTRATOR_CHANNEL_ID = "1485795618185154662"
SLEEP_SECONDS = 600  # 10 minutes


# --- Database queries --------------------------------------------------------

def query_open_projects(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, status, priority, target_date FROM projects "
        "WHERE status NOT IN ('completed', 'archived')"
    )
    return cur.fetchall()


def query_open_tasks(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT t.id, t.title, t.status, t.priority, t.due_date, p.name AS project_name "
        "FROM project_tasks t "
        "JOIN projects p ON t.project_id = p.id "
        "WHERE t.status != 'done'"
    )
    return cur.fetchall()


# --- Build plain-text summary ------------------------------------------------

def build_data_summary(projects, tasks):
    today = datetime.date.today().isoformat()
    lines = []

    lines.append(f"=== Open Projects ({len(projects)}) ===")
    if projects:
        for pid, name, status, priority, target_date in projects:
            overdue = ""
            if target_date and target_date < today:
                overdue = " [OVERDUE]"
            lines.append(
                f"  [{pid}] {name} | status={status} | priority={priority} "
                f"| due={target_date or 'N/A'}{overdue}"
            )
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append(f"=== Open Tasks ({len(tasks)}) ===")
    if tasks:
        for tid, title, status, priority, due_date, project_name in tasks:
            overdue = ""
            if due_date and due_date < today:
                overdue = " [OVERDUE]"
            lines.append(
                f"  [{tid}] {title} | project={project_name} | status={status} "
                f"| priority={priority} | due={due_date or 'N/A'}{overdue}"
            )
    else:
        lines.append("  (none)")

    return "\n".join(lines)


# --- Discord posting ---------------------------------------------------------

def post_to_discord(message_text):
    token = os.environ.get("DISCORD_BOT_TOKEN")
    channel_id = os.environ.get("DISCORD_CHANNEL_ID")

    if not token or not channel_id:
        print("  [Discord] DISCORD_BOT_TOKEN or DISCORD_CHANNEL_ID not set — skipping Discord post.")
        return

    url = DISCORD_API_URL.format(channel_id=channel_id)
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }

    # Discord has a 2000 char message limit; truncate if needed
    if len(message_text) > 1900:
        message_text = message_text[:1897] + "..."

    payload = {"content": message_text}
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    response.raise_for_status()


# --- State management --------------------------------------------------------

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("seen_project_ids", [])), set(data.get("seen_task_ids", []))
    return set(), set()


def save_state(seen_project_ids, seen_task_ids):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "seen_project_ids": sorted(seen_project_ids),
            "seen_task_ids": sorted(seen_task_ids),
        }, f)


# --- Orchestrator Discord alert ----------------------------------------------

def post_new_items_to_orchestrator(new_projects, new_tasks, projects_by_id):
    """Post new projects/tasks to the orchestrator channel for assignment."""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("  [Discord] DISCORD_BOT_TOKEN not set — skipping orchestrator alert.")
        return

    lines = ["🆕 NEW ITEMS — Orchestrator Assignment Needed"]

    lines.append("\nProjects:")
    if new_projects:
        for pid, name, status, priority, target_date in new_projects:
            lines.append(f"• [ID: {pid}] {name} (Priority: {priority or 'N/A'})")
    else:
        lines.append("• (none)")

    lines.append("\nTasks:")
    if new_tasks:
        for tid, title, status, priority, due_date, project_name in new_tasks:
            lines.append(
                f"• [ID: {tid}] {title} → Project: {project_name} (Priority: {priority or 'N/A'})"
            )
    else:
        lines.append("• (none)")

    lines.append("\nPlease assign these to the appropriate team member.")

    message_text = "\n".join(lines)
    if len(message_text) > 1900:
        message_text = message_text[:1897] + "..."

    url = DISCORD_API_URL.format(channel_id=ORCHESTRATOR_CHANNEL_ID)
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, json={"content": message_text}, headers=headers, timeout=30)
    response.raise_for_status()


# --- Save report file --------------------------------------------------------

def save_report(summary_text, projects, tasks):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.txt"
    filepath = os.path.join(REPORTS_DIR, filename)

    header = (
        f"Business Monitor Report\n"
        f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Open projects: {len(projects)} | Open tasks: {len(tasks)}\n"
        f"{'=' * 60}\n\n"
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(header + summary_text)

    return filepath


# --- Single monitor cycle ----------------------------------------------------

def run_cycle():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = sqlite3.connect(DB_PATH)
    except Exception as e:
        print(f"[{now_str}] ERROR connecting to DB: {e}")
        return

    try:
        projects = query_open_projects(conn)
        tasks = query_open_tasks(conn)
    except Exception as e:
        print(f"[{now_str}] ERROR querying DB: {e}")
        conn.close()
        return
    finally:
        conn.close()

    # --- New item detection --------------------------------------------------
    seen_project_ids, seen_task_ids = load_state()

    new_projects = [p for p in projects if p[0] not in seen_project_ids]
    new_tasks = [t for t in tasks if t[0] not in seen_task_ids]

    if new_projects or new_tasks:
        print(
            f"[{now_str}] New items detected — {len(new_projects)} project(s), "
            f"{len(new_tasks)} task(s). Alerting orchestrator."
        )
        try:
            post_new_items_to_orchestrator(new_projects, new_tasks, {})
        except Exception as e:
            print(f"[{now_str}] ERROR posting orchestrator alert: {e}")
    else:
        print(f"[{now_str}] No new items since last check.")

    # Update state with all currently open IDs
    save_state(
        {p[0] for p in projects},
        {t[0] for t in tasks},
    )
    # -------------------------------------------------------------------------

    if not projects and not tasks:
        summary = "All clear — no open items."
    else:
        summary = build_data_summary(projects, tasks)

    # Post to Discord
    try:
        post_to_discord(summary)
    except Exception as e:
        print(f"[{now_str}] ERROR posting to Discord: {e}")

    # Save report file
    try:
        filepath = save_report(summary, projects, tasks)
    except Exception as e:
        print(f"[{now_str}] ERROR saving report: {e}")
        filepath = "(save failed)"

    print(
        f"[{now_str}] Checked DB — {len(projects)} projects, {len(tasks)} tasks. "
        f"Report saved: {os.path.basename(filepath) if filepath != '(save failed)' else filepath}"
    )


# --- Entry point -------------------------------------------------------------

def main():
    once = "--once" in sys.argv

    if once:
        run_cycle()
    else:
        while True:
            run_cycle()
            time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
