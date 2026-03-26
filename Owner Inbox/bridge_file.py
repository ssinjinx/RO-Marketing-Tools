#!/usr/bin/env python3
"""Simple file-based bridge for dashboard chat."""
import os
import sys
import time
import socketio

INPUT_FILE = "/tmp/orchestrator_input.txt"
OUTPUT_FILE = "/tmp/orchestrator_output.txt"

sio = socketio.Client(reconnection=True)

@sio.event
def connect():
    sio.emit('bridge_register')
    with open(OUTPUT_FILE, "a") as f:
        f.write("=== Bridge connected ===\n")

@sio.on('chat_message')
def on_message(data):
    msg = f"[USER] {data.get('content', '')}\n"
    with open(OUTPUT_FILE, "a") as f:
        f.write(msg)
    print(msg, end="", flush=True)

@sio.on('bridge_connected')
def on_connected(data):
    msg = f"=== Bridge ready (queued: {data.get('queued', 0)}) ===\n"
    with open(OUTPUT_FILE, "a") as f:
        f.write(msg)
    print(msg, end="", flush=True)

@sio.on('chat_response')
def on_response(data):
    msg = f"[ECHO] {data.get('content', '')}\n"
    with open(OUTPUT_FILE, "a") as f:
        f.write(msg)

def send_response(text):
    sio.emit('chat_response', {'content': text, 'role': 'assistant'})
    with open(OUTPUT_FILE, "a") as f:
        f.write(f"[ORCHESTRATOR] {text}\n")

# Create input file if not exists
if not os.path.exists(INPUT_FILE):
    open(INPUT_FILE, "w").close()

print(f"Bridge connecting to localhost:5000...")
print(f"Type responses in file: {INPUT_FILE}")
print(f"Messages appear in: {OUTPUT_FILE}")
print("=" * 50)

sio.connect('http://localhost:5000')

# Watch input file for responses
last_size = 0
while True:
    try:
        current_size = os.path.getsize(INPUT_FILE)
        if current_size > last_size:
            with open(INPUT_FILE, "r") as f:
                f.seek(last_size)
                new_text = f.read().strip()
                if new_text:
                    send_response(new_text)
                    # Clear file after reading
                    open(INPUT_FILE, "w").close()
                    last_size = 0
                else:
                    last_size = current_size
        time.sleep(0.1)
    except KeyboardInterrupt:
        break

sio.disconnect()
