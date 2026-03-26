#!/usr/bin/env python3
"""
Terminal Bridge for Dashboard Chat (FIFO version)

Uses a named pipe for receiving responses from the orchestrator.

Usage:
  1. Run: python3 bridge_fifo.py
  2. Bridge shows messages from dashboard
  3. Send responses by writing to the FIFO:
     echo "your response" > /tmp/orchestrator_responses
"""

import os
import sys
import time
import socketio

SERVER_URL = "http://localhost:5000"
FIFO_PATH = "/tmp/orchestrator_responses"

# Create FIFO if it doesn't exist
if not os.path.exists(FIFO_PATH):
    os.mkfifo(FIFO_PATH)

sio = socketio.Client(reconnection=True, reconnection_delay=5)

@sio.event
def connect():
    print("\n" + "="*60)
    print(" Connected to server")
    print("="*60 + "\n")
    sio.emit('bridge_register')

@sio.event
def disconnect():
    print("\n" + "="*60)
    print(" Disconnected from server")
    print("="*60 + "\n")

@sio.on('chat_message')
def on_chat_message(data):
    content = data.get('content', '')
    role = data.get('role', 'user')
    timestamp = data.get('timestamp', time.strftime('%H:%M:%S'))

    if role == 'user':
        print(f"\n[{timestamp}] [USER] {content}")
    else:
        print(f"\n[{timestamp}] [{role.upper()}] {content}")
    print("> ", end="", flush=True)

@sio.on('bridge_connected')
def on_bridge_connected(data):
    status = data.get('status', 'unknown')
    queued = data.get('queued', 0)
    print(f"\n" + "="*60)
    print(f" Bridge registered (status: {status}, queued: {queued})")
    print("="*60)
    print(f"\nSend responses by writing to: {FIFO_PATH}")
    print(f"  Example: echo 'your message' > {FIFO_PATH}")
    print("\n" + "-"*60)
    print("> ", end="", flush=True)

@sio.on('bridge_status')
def on_bridge_status(data):
    pass  # Ignore status updates

def response_reader():
    """Read responses from FIFO and send to dashboard."""
    while True:
        try:
            with open(FIFO_PATH, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and sio.connected:
                        sio.emit('chat_response', {'content': line, 'role': 'assistant'})
                        print(f"\n[Sent] {line}")
                        print("> ", end="", flush=True)
        except Exception as e:
            time.sleep(0.1)

import threading
reader_thread = threading.Thread(target=response_reader, daemon=True)
reader_thread.start()

print("="*60)
print(" Terminal Bridge Starting (FIFO mode)")
print("="*60)
print(f"Connecting to: {SERVER_URL}")
print(f"Response FIFO: {FIFO_PATH}")
print("\nSend responses with:")
print(f'  echo "your message" > {FIFO_PATH}')
print("-"*60)

while True:
    try:
        sio.connect(SERVER_URL)
        sio.wait()
    except Exception as e:
        print(f"Connection error: {e}")
        print("Retrying in 5 seconds...")
        time.sleep(5)
