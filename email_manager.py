#!/usr/bin/env python3
"""
Email Manager - Local web UI for Gmail management via GWS CLI
Run: python3 email_manager.py
Access: http://localhost:5001
"""

import subprocess
import re
import json
import os
from flask import Flask, render_template_string, request, jsonify, redirect, url_for

app = Flask(__name__)

# ============ GWS CLI Helpers ============

def gws_run(args):
    """Run GWS CLI command and return output"""
    # args like ['gmail', 'search', 'query', '--max', '50']
    # Insert -a ssinjin after the subcommand (first arg)
    cmd = ['uvx', 'gws-cli']
    if args:
        cmd.append(args[0])  # e.g., 'gmail'
        cmd.extend(['-a', 'ssinjin'])  # account flag
        cmd.extend(args[1:])  # rest of args
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout

def parse_messages(text):
    """Extract message list from GWS CLI output"""
    idx = text.find('"data":')
    if idx < 0:
        return []
    idx += 7
    while idx < len(text) and text[idx] != '[':
        idx += 1
    start = idx
    while idx < len(text) and text[idx] != ']':
        idx += 1
    end = idx + 1
    data_str = text[start:end].replace('\\"', '"')
    try:
        return json.loads(data_str)
    except:
        return []

def search_emails(query, max_results=50):
    """Search emails and return list of dicts with id, from, subject, date, snippet"""
    output = gws_run(['gmail', 'search', query, '--max', str(max_results)])
    messages = parse_messages(output)
    return messages

def get_labels():
    """Get all labels"""
    output = gws_run(['gmail', 'labels'])
    try:
        data = json.loads(output)
        labels = []
        for entry in data.get('labels', []):
            if entry.get('type') == 'user':
                labels.append({'id': entry['id'], 'name': entry['name']})
        return labels
    except:
        return []

def trash_email(message_id):
    """Move email to trash"""
    output = gws_run(['gmail', 'trash', message_id])
    return 'error' not in output.lower()

def delete_email(message_id):
    """Permanently delete email"""
    output = gws_run(['gmail', 'delete', message_id])
    return 'error' not in output.lower()

def batch_trash(message_ids):
    """Move multiple emails to trash"""
    if not message_ids:
        return 0
    ids_str = ','.join(message_ids[:100])
    output = gws_run(['gmail', 'batch-modify', ids_str, '--remove-labels', 'INBOX'])
    return len(message_ids)

# ============ Templates ============

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Email Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; color: #eee; min-height: 100vh;
        }
        .container { max-width: 1000px; margin: 0 auto; padding: 20px; }
        h1 { color: #00d4aa; margin-bottom: 20px; }
        .search-box {
            background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 20px;
        }
        .search-box input[type="text"] {
            width: 70%; padding: 12px; border: 1px solid #333; border-radius: 5px;
            background: #0f0f23; color: #fff; font-size: 14px;
        }
        .search-box select {
            padding: 12px; border: 1px solid #333; border-radius: 5px;
            background: #0f0f23; color: #fff; margin-left: 10px;
        }
        .search-box button {
            padding: 12px 25px; background: #00d4aa; color: #1a1a2e; border: none;
            border-radius: 5px; cursor: pointer; font-weight: bold; margin-left: 10px;
        }
        .search-box button:hover { background: #00b894; }
        .search-box .quick-btns { margin-top: 10px; }
        .quick-btns button {
            background: #16213e; color: #00d4aa; border: 1px solid #00d4aa;
            padding: 8px 15px; margin: 5px 5px 0 0; border-radius: 5px; cursor: pointer;
        }
        .quick-btns button:hover { background: #1a2a4e; }
        .actions {
            background: #16213e; padding: 15px; border-radius: 10px; margin-bottom: 20px;
            display: flex; gap: 10px; align-items: center;
        }
        .actions button {
            padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold;
        }
        .btn-trash { background: #e74c3c; color: white; }
        .btn-delete { background: #8e44ad; color: white; }
        .btn-select { background: #3498db; color: white; }
        .btn-select:hover { background: #2980b9; }
        .btn-trash:hover { background: #c0392b; }
        .btn-delete:hover { background: #732d91; }
        .email-count { color: #888; margin-left: auto; }
        .email-list { list-style: none; }
        .email-item {
            background: #16213e; padding: 15px; margin-bottom: 10px; border-radius: 8px;
            display: flex; align-items: flex-start; gap: 15px;
        }
        .email-item input[type="checkbox"] { margin-top: 5px; transform: scale(1.3); }
        .email-content { flex: 1; min-width: 0; }
        .email-from { color: #00d4aa; font-weight: bold; font-size: 14px; }
        .email-subject { color: #fff; margin: 5px 0; font-size: 15px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .email-snippet { color: #888; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .email-date { color: #666; font-size: 12px; white-space: nowrap; }
        .email-id { color: #444; font-size: 11px; margin-top: 5px; }
        .empty { text-align: center; color: #666; padding: 50px; }
        .success { background: #27ae60; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .error { background: #e74c3c; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .label-tag {
            display: inline-block; background: #2c3e50; color: #00d4aa;
            padding: 3px 8px; border-radius: 3px; font-size: 11px; margin-right: 5px;
        }
        .search-tip { color: #666; font-size: 12px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Email Manager</h1>

        {% if success %}
        <div class="success">{{ success }}</div>
        {% endif %}
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}

        <div class="search-box">
            <form method="GET" action="/">
                <input type="text" name="q" value="{{ query }}" placeholder="Search emails... (e.g., from:amazon.com, subject:invoice, is:unread)">
                <select name="label">
                    <option value="">All Labels</option>
                    {% for label in labels %}
                    <option value="{{ label.name }}" {% if label.name == selected_label %}selected{% endif %}>{{ label.name }}</option>
                    {% endfor %}
                </select>
                <button type="submit">Search</button>
            </form>
            <div class="quick-btns">
                <button onclick="location.href='/?q=is:unread'">Unread</button>
                <button onclick="location.href='/?q=is:starred'">Starred</button>
                <button onclick="location.href='/?q=after:2026/03/01'">This Month</button>
                <button onclick="location.href='/?q=has:attachment'">Has Attachments</button>
                <button onclick="location.href='/?q=label:Junk'">Junk</button>
            </div>
            <div class="search-tip">
                <strong>Tips:</strong> Use Gmail search operators: <code>from:</code> <code>subject:</code> <code>after:</code> <code>before:</code> <code>has:attachment</code> <code>is:unread</code>
            </div>
        </div>

        {% if messages %}
        <div class="actions">
            <button class="btn-select" onclick="selectAll()">Select All</button>
            <button class="btn-select" onclick="selectNone()">Select None</button>
            <span class="email-count">{{ messages|length }} emails found</span>
            <button class="btn-trash" onclick="trashSelected()">Move to Trash</button>
            <button class="btn-delete" onclick="deleteSelected()">Delete Forever</button>
        </div>

        <form id="email-form" method="POST" action="/delete">
            <input type="hidden" name="action" id="action-type" value="">
            <ul class="email-list">
                {% for msg in messages %}
                <li class="email-item">
                    <input type="checkbox" name="ids" value="{{ msg.id }}">
                    <div class="email-content">
                        <div class="email-from">{{ msg.from }}</div>
                        <div class="email-subject">{{ msg.subject }}</div>
                        <div class="email-snippet">{{ msg.snippet }}</div>
                        {% if msg.thread_id %}
                        <div class="email-id">Thread: {{ msg.thread_id[:16] }}... | ID: {{ msg.id[:16] }}...</div>
                        {% endif %}
                    </div>
                    <div class="email-date">{{ msg.date }}</div>
                </li>
                {% endfor %}
            </ul>
        </form>
        {% elif query %}
        <div class="empty">No emails found for "{{ query }}"</div>
        {% else %}
        <div class="empty">Enter a search query above to find emails</div>
        {% endif %}
    </div>

    <script>
        function selectAll() {
            document.querySelectorAll('input[name="ids"]').forEach(cb => cb.checked = true);
        }
        function selectNone() {
            document.querySelectorAll('input[name="ids"]').forEach(cb => cb.checked = false);
        }
        function getSelected() {
            return Array.from(document.querySelectorAll('input[name="ids"]:checked')).map(cb => cb.value);
        }
        function trashSelected() {
            const ids = getSelected();
            if (ids.length === 0) { alert('No emails selected'); return; }
            if (!confirm(`Move ${ids.length} email(s) to trash?`)) return;
            document.getElementById('action-type').value = 'trash';
            document.getElementById('email-form').submit();
        }
        function deleteSelected() {
            const ids = getSelected();
            if (ids.length === 0) { alert('No emails selected'); return; }
            if (!confirm(`PERMANENTLY delete ${ids.length} email(s)? This cannot be undone!`)) return;
            document.getElementById('action-type').value = 'delete';
            document.getElementById('email-form').submit();
        }
    </script>
</body>
</html>
'''

# ============ Routes ============

@app.route('/')
def index():
    query = request.args.get('q', '')
    selected_label = request.args.get('label', '')
    messages = []
    labels = get_labels()

    if query:
        if selected_label:
            query = f'{query} label:{selected_label}'
        messages = search_emails(query)

    return render_template_string(HTML_TEMPLATE,
                                  messages=messages,
                                  query=query,
                                  selected_label=selected_label,
                                  labels=labels,
                                  success=request.args.get('success', ''),
                                  error=request.args.get('error', ''))

@app.route('/delete', methods=['POST'])
def delete_route():
    action = request.form.get('action', '')
    ids = request.form.getlist('ids')

    if not ids:
        return redirect(url_for('index', error='No emails selected'))

    success_count = 0
    for msg_id in ids:
        if action == 'trash':
            if trash_email(msg_id):
                success_count += 1
        elif action == 'delete':
            if delete_email(msg_id):
                success_count += 1

    action_word = 'trashed' if action == 'trash' else 'deleted'
    return redirect(url_for('index', success=f'{success_count} email(s) moved to trash'))

# ============ Main ============

if __name__ == '__main__':
    print("=" * 50)
    print("Email Manager - Local Only")
    print("=" * 50)
    print("URL: http://localhost:5001")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    app.run(host='127.0.0.1', port=5001, debug=False)
