#!/usr/bin/env python3
"""
Reply script for dashboard chat bridge.
Usage: ./reply "Your response message here"
"""

import sys
import sqlite3
import os

def send_reply(message):
    db_path = os.path.join(os.path.dirname(__file__), 'instance', 'owner_inbox.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO chat_messages (direction, content, sender, read) VALUES ('out', ?, 'orchestrator', 0)",
        (message,)
    )
    conn.commit()
    conn.close()
    print(f"✓ Sent to dashboard: {message[:60]}{'...' if len(message) > 60 else ''}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: ./reply 'Your message here'")
        print("Example: ./reply 'I'll have Maya work on that'")
        sys.exit(1)
    
    message = ' '.join(sys.argv[1:])
    send_reply(message)
