#!/usr/bin/env python3
"""
Terminal Bridge for Dashboard Chat - Pipe Version

Reads responses from a named pipe so the orchestrator can send messages
by writing to the pipe.

Usage:
  1. Start this bridge: python3 bridge_pipe.py
  2. Send messages by writing to /tmp/orchestrator_response:
     echo "Your response here" > /tmp/orchestrator_response
"""

import os
import sys
import time
import threading
import socketio

SERVER_URL = "http://localhost:5000"
PIPE_PATH = "/tmp/orchestrator_response"

# Create named pipe if it doesn't exist
if not os.path.exists(PIPE_PATH):
    os.mkfifo(PIPE_PATH)

sio = socketio.Client(reconnection=True, reconnection_delay=5)
connected = False

@sio.event
def connect():
    global connected
    connected = True
    print("=" * 60)
    print(" CONNECTED - Bridge active")
    print("=" * 60)
    sio.emit('bridge_register')

@sio.event
def disconnect():
    global connected
    connected = False
    print("\nDisconnected from server")

@sio.on('chat_message')
def on_chat_message(data):
    content = data.get('content', '')
    role = data.get('role', 'user')
    print(f"\n[USER] {content}\n")
    sys.stdout.flush()

@sio.on('bridge_connected')
def on_bridge_connected(data):
    print(f"Bridge registered. Status: {data}")

def send_response(text):
    if connected:
        sio.emit('chat_response', {'content': text, 'role': 'assistant'})
        print(f"\n[ORCHESTRATOR] {text}\n")
    else:
        print("Not connected, can't send response")

def pipe_reader():
    """Read responses from the named pipe."""
    print(f"\nListening for responses on: {PIPE_PATH}")
    print("To respond, run: echo 'your message' > /tmp/orchestrator_response")
    print()
    while True:
        try:
            with open(PIPE_PATH, 'r') as pipe:
                for line in pipe:
                    text = line.strip()
                    if text:
                        send_response(text)
        except Exception as e:
            print(f"Pipe error: {e}")
            time.sleep(1)

def main():
    print("=" * 60)
    print(" Terminal Bridge Starting")
    print("=" * 60)
    print(f"Connecting to: {SERVER_URL}")

    # Start pipe reader in background thread
    pipe_thread = threading.Thread(target=pipe_reader, daemon=True)
    pipe_thread.start()

    # Connect to server
    while True:
        try:
            sio.connect(SERVER_URL)
            sio.wait()
        except KeyboardInterrupt:
            print("\nShutting down...")
            break
        except Exception as e:
            print(f"Connection error: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == '__main__':
    main()
