#!/usr/bin/env python3
"""
chat_bridge.py — Dashboard Chat → Orchestrator Bridge

Polls the chat_messages table for unread inbound messages (direction='in', read=0),
forwards each one to the orchestrator's Discord channel, then marks them read.

Usage:
    python3 chat_bridge.py          # poll continuously (every 5s)
    python3 chat_bridge.py --once   # single poll, then exit
    python3 chat_bridge.py --interval 30  # poll every 30s

Orchestrator replies by using reply.py or writing to the DB directly.
"""

import sqlite3
import requests
import time
import datetime
import os
import sys
import json
import argparse


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

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'owner_inbox.db')
DISCORD_API_URL = "https://discord.com/api/v10/channels/{channel_id}/messages"
ORCHESTRATOR_CHANNEL_ID = "1485795618185154662"
DEFAULT_INTERVAL = 5  # seconds between polls


# --- Database ----------------------------------------------------------------

def fetch_unread_messages(conn):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, content, sender, created_at FROM chat_messages "
        "WHERE direction = 'in' AND read = 0 "
        "ORDER BY created_at ASC"
    )
    return cur.fetchall()


def mark_as_read(conn, msg_ids):
    if not msg_ids:
        return
    placeholders = ','.join('?' * len(msg_ids))
    conn.execute(
        f"UPDATE chat_messages SET read = 1 WHERE id IN ({placeholders})",
        msg_ids
    )
    conn.commit()


# --- Discord -----------------------------------------------------------------

def post_to_discord(channel_id, text):
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("  [Discord] DISCORD_BOT_TOKEN not set — skipping.")
        return False

    url = DISCORD_API_URL.format(channel_id=channel_id)
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
    }

    if len(text) > 1900:
        text = text[:1897] + "..."

    response = requests.post(url, json={"content": text}, headers=headers, timeout=30)
    response.raise_for_status()
    return True


def format_for_orchestrator(msg_id, sender, content, created_at):
    return (
        f"📬 **Dashboard Message** [id={msg_id}]\n"
        f"From: {sender} | {created_at}\n\n"
        f"{content}\n\n"
        f"_To reply: `python3 reply.py \"your response\"` or write to DB._"
    )


# --- Poll cycle --------------------------------------------------------------

def run_cycle():
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        conn = sqlite3.connect(DB_PATH)
    except Exception as e:
        print(f"[{now_str}] ERROR connecting to DB: {e}")
        return

    try:
        messages = fetch_unread_messages(conn)
    except Exception as e:
        print(f"[{now_str}] ERROR querying DB: {e}")
        conn.close()
        return

    if not messages:
        return  # nothing to do, stay quiet

    print(f"[{now_str}] {len(messages)} unread message(s) — forwarding to orchestrator.")

    forwarded_ids = []
    for msg_id, content, sender, created_at in messages:
        text = format_for_orchestrator(msg_id, sender or 'user', content, created_at)
        try:
            posted = post_to_discord(ORCHESTRATOR_CHANNEL_ID, text)
            if posted:
                forwarded_ids.append(msg_id)
                print(f"  [→ Discord] msg_id={msg_id}: {content[:60]}{'...' if len(content) > 60 else ''}")
            else:
                print(f"  [SKIP] msg_id={msg_id}: Discord not configured — will retry.")
        except Exception as e:
            print(f"  [ERROR] msg_id={msg_id}: {e}")
            # Do NOT add to forwarded_ids — retry on next cycle.

    if forwarded_ids:
        try:
            mark_as_read(conn, forwarded_ids)
            print(f"  [DB] Marked {len(forwarded_ids)} message(s) as read.")
        except Exception as e:
            print(f"  [ERROR] marking read: {e}")

    conn.close()


# --- Entry point -------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Dashboard chat → orchestrator bridge")
    parser.add_argument("--once", action="store_true", help="Run one poll then exit")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help=f"Seconds between polls (default: {DEFAULT_INTERVAL})")
    args = parser.parse_args()

    if args.once:
        run_cycle()
        return

    print(f"[chat_bridge] Started — polling every {args.interval}s. Ctrl+C to stop.")
    while True:
        try:
            run_cycle()
        except Exception as e:
            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{ts}] Unhandled error in run_cycle: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
