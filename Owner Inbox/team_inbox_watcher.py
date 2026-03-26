#!/usr/bin/env python3
"""
Team Inbox Watcher
Monitors Team Inbox directory for new .md task files and routes them to agents.
Uses polling-based monitoring (no watchdog dependency).
"""

import os
import re
import time
import sqlite3
from datetime import datetime
from pathlib import Path

# Configuration
TEAM_INBOX_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Team Inbox')
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'owner_inbox.db')
POLL_INTERVAL = 2  # seconds between directory scans

# Discord webhook (optional)
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK_URL', '')


def send_discord_notification(message):
    """Send notification to Discord webhook if configured."""
    if not DISCORD_WEBHOOK:
        return
    try:
        import requests
        requests.post(DISCORD_WEBHOOK, json={"content": message}, timeout=5)
    except Exception as e:
        print(f"Discord notification failed: {e}")


class TaskParser:
    """Parse markdown task files to extract project details."""

    @staticmethod
    def parse(filepath):
        """Extract task details from markdown file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract project name (first h1)
            name_match = re.search(r'^# (.+)$', content, re.MULTILINE)
            name = name_match.group(1).strip() if name_match else 'Unknown Project'

            # Extract suggested agent
            agent_match = re.search(r'\*\*Suggested Agent:\*\* (.+)$', content, re.MULTILINE)
            suggested_agent = agent_match.group(1).strip() if agent_match else None

            # Extract priority
            priority_match = re.search(r'\*\*Priority:\*\* (.+)$', content, re.MULTILINE)
            priority = priority_match.group(1).strip() if priority_match else 'medium'

            # Extract description (from ## Description section)
            desc_match = re.search(r'## Description\n\n(.+?)(?=\n##|\Z)', content, re.DOTALL)
            description = desc_match.group(1).strip() if desc_match else ''

            return {
                'name': name,
                'suggested_agent': suggested_agent,
                'priority': priority,
                'description': description,
                'filepath': filepath
            }
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return None


class DatabaseManager:
    """Manage agent database updates."""

    def __init__(self, db_path):
        self.db_path = db_path

    def get_db(self):
        """Get database connection."""
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    def get_agent_by_name(self, name):
        """Get agent by name."""
        db = self.get_db()
        cursor = db.execute("SELECT * FROM agents WHERE name = ?", (name,))
        agent = cursor.fetchone()
        db.close()
        return agent

    def update_agent_task(self, agent_name, task):
        """Update agent status to working and set current task."""
        db = self.get_db()
        try:
            db.execute(
                """UPDATE agents SET status = 'working', current_task = ?, updated_at = datetime('now')
                   WHERE name = ? AND status != 'working'""",
                (task, agent_name)
            )
            db.commit()
            rows_updated = db.total_changes
            db.close()
            return rows_updated > 0
        except Exception as e:
            print(f"Database error: {e}")
            db.close()
            return False

    def get_agent_list(self):
        """Get list of all agents."""
        db = self.get_db()
        cursor = db.execute("SELECT name, status, current_task FROM agents ORDER BY name")
        agents = cursor.fetchall()
        db.close()
        return agents


class TeamInboxWatcher:
    """Poll-based watcher for Team Inbox directory."""

    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.processed_files = set()
        self.parser = TaskParser()

    def scan_directory(self):
        """Scan Team Inbox for new .md files."""
        inbox_path = Path(TEAM_INBOX_PATH)
        if not inbox_path.exists():
            return []

        md_files = list(inbox_path.glob('*.md'))
        new_files = [str(f) for f in md_files if str(f) not in self.processed_files]
        return new_files

    def process_file(self, filepath):
        """Process a single task file."""
        if filepath in self.processed_files:
            return

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] New task file detected: {os.path.basename(filepath)}")

        # Parse the task file
        task = self.parser.parse(filepath)
        if not task:
            print(f"  ⚠️  Could not parse task file")
            return

        print(f"  📋 Project: {task['name']}")
        print(f"  🎯 Suggested Agent: {task['suggested_agent']}")
        print(f"  📊 Priority: {task['priority']}")

        # Get the suggested agent
        agent_name = task['suggested_agent']
        if not agent_name:
            print(f"  ⚠️  No agent specified in task file")
            return

        # Check if agent exists
        agent = self.db_manager.get_agent_by_name(agent_name)
        if not agent:
            print(f"  ⚠️  Agent '{agent_name}' not found in database")
            return

        # Update agent status
        task_summary = f"{task['name']}: {task['description'][:80]}..." if len(task['description']) > 80 else task['description']
        updated = self.db_manager.update_agent_task(agent_name, task_summary)

        if updated:
            print(f"  ✅ Assigned to {agent_name} (status: working)")

            # Send Discord notification
            send_discord_notification(
                f"🎯 **New Task Assigned**\n"
                f"**Agent:** {agent_name}\n"
                f"**Project:** {task['name']}\n"
                f"**Priority:** {task['priority']}\n"
                f"Check Team Inbox for details."
            )
        else:
            print(f"  ℹ️  {agent_name} is already working on a task")

        self.processed_files.add(filepath)

    def scan_existing_files(self):
        """Mark existing .md files as already processed on startup."""
        inbox_path = Path(TEAM_INBOX_PATH)
        if not inbox_path.exists():
            print(f"Creating Team Inbox directory: {TEAM_INBOX_PATH}")
            inbox_path.mkdir(parents=True, exist_ok=True)
            return

        md_files = list(inbox_path.glob('*.md'))
        if md_files:
            print(f"Found {len(md_files)} existing task file(s)")
            for md_file in md_files:
                self.processed_files.add(str(md_file))


def main():
    """Main watcher loop."""
    print("=" * 60)
    print("Team Inbox Watcher")
    print("=" * 60)
    print(f"📁 Watching: {TEAM_INBOX_PATH}")
    print(f"🗄️  Database: {DB_PATH}")
    print(f"🔔 Discord: {'Enabled' if DISCORD_WEBHOOK else 'Disabled'}")
    print("=" * 60)

    # Initialize database manager
    db_manager = DatabaseManager(DB_PATH)

    # Show current agent status
    print("\n📊 Current Agent Status:")
    agents = db_manager.get_agent_list()
    for agent in agents:
        status_icon = "🟢" if agent['status'] == 'idle' else "🔴"
        task_info = f" | Task: {agent['current_task'][:40]}..." if agent['current_task'] else ""
        print(f"  {status_icon} {agent['name']}: {agent['status']}{task_info}")
    print()

    # Create watcher
    watcher = TeamInboxWatcher(db_manager)
    watcher.scan_existing_files()

    print(f"\n👂 Watching for new task files... (polling every {POLL_INTERVAL}s, Press Ctrl+C to stop)\n")

    try:
        while True:
            new_files = watcher.scan_directory()
            for filepath in new_files:
                # Wait briefly to ensure file is fully written
                time.sleep(0.5)
                watcher.process_file(filepath)
            time.sleep(POLL_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping watcher...")

    print("✅ Watcher stopped.")


if __name__ == '__main__':
    main()
