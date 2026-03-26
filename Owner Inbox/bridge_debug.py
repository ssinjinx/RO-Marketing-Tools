#!/usr/bin/env python3
import sys
import socketio
import time

sio = socketio.Client(logger=True, engineio_logger=True)

@sio.event
def connect():
    print("Connected!")
    sio.emit('bridge_register')

@sio.event
def disconnect():
    print("Disconnected!")

@sio.on('chat_message')
def on_chat_message(data):
    print(f"\n[USER] {data.get('content', '')}")

@sio.on('bridge_connected')
def on_bridge_connected(data):
    print(f"Bridge registered: {data}")

@sio.on('chat_response')
def on_chat_response(data):
    print(f"Response echo: {data}")

print("Connecting...")
try:
    sio.connect('http://localhost:5000')
    sio.wait()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
