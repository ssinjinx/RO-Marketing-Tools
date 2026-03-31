import os
import re
import secrets
import datetime
import smtplib
import socket
import subprocess
import threading
import uuid
import requests as http_requests
from flask import Flask, render_template, request, redirect, url_for, flash, g, session, jsonify
from database import get_db, close_db, init_db
from apify_client import ApifyClient
import anthropic
from flask_socketio import SocketIO, emit


def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())


load_env()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'fallback-dev-key')
app.config['DATABASE'] = os.path.join(app.instance_path, 'owner_inbox.db')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'fallback-dev-key')

os.makedirs(app.instance_path, exist_ok=True)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

app.teardown_appcontext(close_db)

PIN = "6911"


@app.before_request
def check_pin():
    if request.endpoint in ('lock', 'unlock', 'static', 'chat_send', 'chat_poll', 'chat_history', 'projects_complete'):
        return
    if not session.get('unlocked'):
        return redirect(url_for('lock'))


@app.route('/lock')
def lock():
    return render_template('lock.html', error=None)


@app.route('/unlock', methods=['POST'])
def unlock():
    if request.form.get('pin') == PIN:
        session['unlocked'] = True
        return redirect(url_for('index'))
    return render_template('lock.html', error='Incorrect PIN. Try again.')


# ─── Dashboard ────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    counts = {
        'files': db.execute("SELECT COUNT(*) FROM files").fetchone()[0],
        'articles': db.execute("SELECT COUNT(*) FROM articles").fetchone()[0],
        'contacts': db.execute("SELECT COUNT(*) FROM contacts").fetchone()[0],
        'deals': db.execute("SELECT COUNT(*) FROM deals").fetchone()[0],
        'active_projects': db.execute(
            "SELECT COUNT(*) FROM projects WHERE status = 'active'"
        ).fetchone()[0],
        'open_tasks': db.execute(
            "SELECT COUNT(*) FROM project_tasks WHERE status != 'done'"
        ).fetchone()[0],
        'working_agents': db.execute(
            "SELECT COUNT(*) FROM agents WHERE status = 'working'"
        ).fetchone()[0],
        'ro_prospects': db.execute("SELECT COUNT(*) FROM prospects").fetchone()[0],
        'ro_new_prospects': db.execute(
            "SELECT COUNT(*) FROM prospects WHERE status = 'new'"
        ).fetchone()[0],
    }
    agents = db.execute('SELECT * FROM agents ORDER BY id').fetchall()
    return render_template('index.html', counts=counts, agents=agents)


# ─── File Catalog ─────────────────────────────────────────────────────────────

@app.route('/files')
def files_list():
    db = get_db()
    files = db.execute("SELECT * FROM files ORDER BY created_at DESC").fetchall()
    return render_template('file_catalog/list.html', files=files)


@app.route('/files/new', methods=['GET', 'POST'])
def files_new():
    if request.method == 'POST':
        db = get_db()
        db.execute(
            "INSERT INTO files (name, file_path, file_type, description, tags) VALUES (?, ?, ?, ?, ?)",
            (request.form['name'], request.form['file_path'],
             request.form.get('file_type'), request.form.get('description'),
             request.form.get('tags'))
        )
        db.commit()
        flash('File added.', 'success')
        return redirect(url_for('files_list'))
    return render_template('file_catalog/form.html', file=None)


@app.route('/files/<int:id>')
def files_view(id):
    db = get_db()
    file = db.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
    if file is None:
        flash('File not found.', 'error')
        return redirect(url_for('files_list'))
    return render_template('file_catalog/view.html', file=file)


@app.route('/files/<int:id>/edit', methods=['GET', 'POST'])
def files_edit(id):
    db = get_db()
    file = db.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
    if file is None:
        flash('File not found.', 'error')
        return redirect(url_for('files_list'))
    if request.method == 'POST':
        db.execute(
            """UPDATE files SET name=?, file_path=?, file_type=?, description=?, tags=?,
               updated_at=datetime('now') WHERE id=?""",
            (request.form['name'], request.form['file_path'],
             request.form.get('file_type'), request.form.get('description'),
             request.form.get('tags'), id)
        )
        db.commit()
        flash('File updated.', 'success')
        return redirect(url_for('files_view', id=id))
    return render_template('file_catalog/form.html', file=file)


@app.route('/files/<int:id>/delete', methods=['POST'])
def files_delete(id):
    db = get_db()
    db.execute("DELETE FROM files WHERE id = ?", (id,))
    db.commit()
    flash('File deleted.', 'success')
    return redirect(url_for('files_list'))


@app.route('/files/<int:id>/download')
def files_download(id):
    from flask import send_from_directory
    db = get_db()
    file = db.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
    if not file or not file['file_path']:
        flash('File not available for download.', 'error')
        return redirect(url_for('files_list'))
    uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    filename = os.path.basename(file['file_path'])
    return send_from_directory(uploads_dir, filename, as_attachment=True)


# ─── Knowledge Base ───────────────────────────────────────────────────────────

@app.route('/kb')
def kb_list():
    db = get_db()
    articles = db.execute("SELECT * FROM articles ORDER BY created_at DESC").fetchall()
    return render_template('knowledge_base/list.html', articles=articles)


@app.route('/kb/new', methods=['GET', 'POST'])
def kb_new():
    if request.method == 'POST':
        db = get_db()
        db.execute(
            "INSERT INTO articles (title, content, category, tags) VALUES (?, ?, ?, ?)",
            (request.form['title'], request.form.get('content'),
             request.form.get('category'), request.form.get('tags'))
        )
        db.commit()
        flash('Article created.', 'success')
        return redirect(url_for('kb_list'))
    return render_template('knowledge_base/form.html', article=None)


@app.route('/kb/<int:id>')
def kb_view(id):
    db = get_db()
    article = db.execute("SELECT * FROM articles WHERE id = ?", (id,)).fetchone()
    if article is None:
        flash('Article not found.', 'error')
        return redirect(url_for('kb_list'))
    return render_template('knowledge_base/view.html', article=article)


@app.route('/kb/<int:id>/edit', methods=['GET', 'POST'])
def kb_edit(id):
    db = get_db()
    article = db.execute("SELECT * FROM articles WHERE id = ?", (id,)).fetchone()
    if article is None:
        flash('Article not found.', 'error')
        return redirect(url_for('kb_list'))
    if request.method == 'POST':
        db.execute(
            """UPDATE articles SET title=?, content=?, category=?, tags=?,
               updated_at=datetime('now') WHERE id=?""",
            (request.form['title'], request.form.get('content'),
             request.form.get('category'), request.form.get('tags'), id)
        )
        db.commit()
        flash('Article updated.', 'success')
        return redirect(url_for('kb_view', id=id))
    return render_template('knowledge_base/form.html', article=article)


@app.route('/kb/<int:id>/delete', methods=['POST'])
def kb_delete(id):
    db = get_db()
    db.execute("DELETE FROM articles WHERE id = ?", (id,))
    db.commit()
    flash('Article deleted.', 'success')
    return redirect(url_for('kb_list'))


# ─── CRM: Contacts ────────────────────────────────────────────────────────────

@app.route('/crm/contacts')
def contacts_list():
    db = get_db()
    contacts = db.execute("SELECT * FROM contacts ORDER BY last_name, first_name").fetchall()
    return render_template('crm/contacts_list.html', contacts=contacts)


@app.route('/crm/contacts/new', methods=['GET', 'POST'])
def contacts_new():
    if request.method == 'POST':
        db = get_db()
        db.execute(
            """INSERT INTO contacts (first_name, last_name, email, phone, company, role, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (request.form['first_name'], request.form.get('last_name'),
             request.form.get('email'), request.form.get('phone'),
             request.form.get('company'), request.form.get('role'),
             request.form.get('notes'))
        )
        db.commit()
        flash('Contact created.', 'success')
        return redirect(url_for('contacts_list'))
    return render_template('crm/contact_form.html', contact=None)


@app.route('/crm/contacts/<int:id>')
def contacts_view(id):
    db = get_db()
    contact = db.execute("SELECT * FROM contacts WHERE id = ?", (id,)).fetchone()
    if contact is None:
        flash('Contact not found.', 'error')
        return redirect(url_for('contacts_list'))
    leads = db.execute("SELECT * FROM leads WHERE contact_id = ?", (id,)).fetchall()
    deals = db.execute("SELECT * FROM deals WHERE contact_id = ?", (id,)).fetchall()
    return render_template('crm/contact_view.html', contact=contact, leads=leads, deals=deals)


@app.route('/crm/contacts/<int:id>/edit', methods=['GET', 'POST'])
def contacts_edit(id):
    db = get_db()
    contact = db.execute("SELECT * FROM contacts WHERE id = ?", (id,)).fetchone()
    if contact is None:
        flash('Contact not found.', 'error')
        return redirect(url_for('contacts_list'))
    if request.method == 'POST':
        db.execute(
            """UPDATE contacts SET first_name=?, last_name=?, email=?, phone=?, company=?,
               role=?, notes=?, updated_at=datetime('now') WHERE id=?""",
            (request.form['first_name'], request.form.get('last_name'),
             request.form.get('email'), request.form.get('phone'),
             request.form.get('company'), request.form.get('role'),
             request.form.get('notes'), id)
        )
        db.commit()
        flash('Contact updated.', 'success')
        return redirect(url_for('contacts_view', id=id))
    return render_template('crm/contact_form.html', contact=contact)


@app.route('/crm/contacts/<int:id>/delete', methods=['POST'])
def contacts_delete(id):
    db = get_db()
    db.execute("DELETE FROM contacts WHERE id = ?", (id,))
    db.commit()
    flash('Contact deleted.', 'success')
    return redirect(url_for('contacts_list'))


# ─── CRM: Leads ───────────────────────────────────────────────────────────────

@app.route('/crm/leads')
def leads_list():
    db = get_db()
    leads = db.execute(
        """SELECT l.*, c.first_name, c.last_name
           FROM leads l LEFT JOIN contacts c ON l.contact_id = c.id
           ORDER BY l.created_at DESC"""
    ).fetchall()
    return render_template('crm/leads_list.html', leads=leads)


@app.route('/crm/leads/new', methods=['GET', 'POST'])
def leads_new():
    db = get_db()
    if request.method == 'POST':
        db.execute(
            """INSERT INTO leads (contact_id, source, status, value, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (request.form.get('contact_id') or None,
             request.form.get('source'), request.form.get('status', 'new'),
             request.form.get('value') or None, request.form.get('notes'))
        )
        db.commit()
        flash('Lead created.', 'success')
        return redirect(url_for('leads_list'))
    contacts = db.execute("SELECT * FROM contacts ORDER BY last_name, first_name").fetchall()
    return render_template('crm/lead_form.html', lead=None, contacts=contacts)


@app.route('/crm/leads/<int:id>/edit', methods=['GET', 'POST'])
def leads_edit(id):
    db = get_db()
    lead = db.execute("SELECT * FROM leads WHERE id = ?", (id,)).fetchone()
    if lead is None:
        flash('Lead not found.', 'error')
        return redirect(url_for('leads_list'))
    if request.method == 'POST':
        db.execute(
            """UPDATE leads SET contact_id=?, source=?, status=?, value=?, notes=?,
               updated_at=datetime('now') WHERE id=?""",
            (request.form.get('contact_id') or None,
             request.form.get('source'), request.form.get('status', 'new'),
             request.form.get('value') or None, request.form.get('notes'), id)
        )
        db.commit()
        flash('Lead updated.', 'success')
        return redirect(url_for('leads_list'))
    contacts = db.execute("SELECT * FROM contacts ORDER BY last_name, first_name").fetchall()
    return render_template('crm/lead_form.html', lead=lead, contacts=contacts)


@app.route('/crm/leads/<int:id>/delete', methods=['POST'])
def leads_delete(id):
    db = get_db()
    db.execute("DELETE FROM leads WHERE id = ?", (id,))
    db.commit()
    flash('Lead deleted.', 'success')
    return redirect(url_for('leads_list'))


# ─── CRM: Deals ───────────────────────────────────────────────────────────────

@app.route('/crm/deals')
def deals_list():
    db = get_db()
    deals = db.execute(
        """SELECT d.*, c.first_name, c.last_name
           FROM deals d LEFT JOIN contacts c ON d.contact_id = c.id
           ORDER BY d.created_at DESC"""
    ).fetchall()
    return render_template('crm/deals_list.html', deals=deals)


@app.route('/crm/deals/new', methods=['GET', 'POST'])
def deals_new():
    db = get_db()
    if request.method == 'POST':
        db.execute(
            """INSERT INTO deals (contact_id, lead_id, title, stage, value, close_date, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (request.form.get('contact_id') or None,
             request.form.get('lead_id') or None,
             request.form['title'], request.form.get('stage'),
             request.form.get('value') or None,
             request.form.get('close_date') or None,
             request.form.get('notes'))
        )
        db.commit()
        flash('Deal created.', 'success')
        return redirect(url_for('deals_list'))
    contacts = db.execute("SELECT * FROM contacts ORDER BY last_name, first_name").fetchall()
    leads = db.execute("SELECT l.*, c.first_name, c.last_name FROM leads l LEFT JOIN contacts c ON l.contact_id = c.id").fetchall()
    stages = db.execute("SELECT * FROM pipeline_stages ORDER BY stage_order").fetchall()
    return render_template('crm/deal_form.html', deal=None, contacts=contacts, leads=leads, stages=stages)


@app.route('/crm/deals/<int:id>/edit', methods=['GET', 'POST'])
def deals_edit(id):
    db = get_db()
    deal = db.execute("SELECT * FROM deals WHERE id = ?", (id,)).fetchone()
    if deal is None:
        flash('Deal not found.', 'error')
        return redirect(url_for('deals_list'))
    if request.method == 'POST':
        db.execute(
            """UPDATE deals SET contact_id=?, lead_id=?, title=?, stage=?, value=?,
               close_date=?, notes=?, updated_at=datetime('now') WHERE id=?""",
            (request.form.get('contact_id') or None,
             request.form.get('lead_id') or None,
             request.form['title'], request.form.get('stage'),
             request.form.get('value') or None,
             request.form.get('close_date') or None,
             request.form.get('notes'), id)
        )
        db.commit()
        flash('Deal updated.', 'success')
        return redirect(url_for('deals_list'))
    contacts = db.execute("SELECT * FROM contacts ORDER BY last_name, first_name").fetchall()
    leads = db.execute("SELECT l.*, c.first_name, c.last_name FROM leads l LEFT JOIN contacts c ON l.contact_id = c.id").fetchall()
    stages = db.execute("SELECT * FROM pipeline_stages ORDER BY stage_order").fetchall()
    return render_template('crm/deal_form.html', deal=deal, contacts=contacts, leads=leads, stages=stages)


@app.route('/crm/deals/<int:id>/delete', methods=['POST'])
def deals_delete(id):
    db = get_db()
    db.execute("DELETE FROM deals WHERE id = ?", (id,))
    db.commit()
    flash('Deal deleted.', 'success')
    return redirect(url_for('deals_list'))


@app.route('/crm/pipeline')
def pipeline():
    db = get_db()
    stages = db.execute("SELECT * FROM pipeline_stages ORDER BY stage_order").fetchall()
    deals_raw = db.execute(
        """SELECT d.*, c.first_name, c.last_name
           FROM deals d LEFT JOIN contacts c ON d.contact_id = c.id"""
    ).fetchall()
    deals_by_stage = {stage['name']: [] for stage in stages}
    for deal in deals_raw:
        stage_name = deal['stage']
        if stage_name in deals_by_stage:
            deals_by_stage[stage_name].append(deal)
        else:
            deals_by_stage.setdefault('(None)', []).append(deal)
    return render_template('crm/pipeline.html', stages=stages, deals_by_stage=deals_by_stage)


# ─── Agent Task Mapping ───────────────────────────────────────────────────────

AGENT_TASK_MAPPING = {
    'ui': 'Maya',
    'development': 'Maya',
    'frontend': 'Maya',
    'backend': 'Maya',
    'flask': 'Maya',
    'web': 'Maya',
    'research': 'Sage',
    'analysis': 'Sage',
    'market': 'Sage',
    'competitive': 'Sage',
    'scrape': 'Kai',
    'scraping': 'Kai',
    'data': 'Kai',
    'apify': 'Kai',
    'pipeline': 'Kai',
    'automation': 'Rex',
    'script': 'Rex',
    'schedule': 'Rex',
    'discord': 'Rex',
    'monitor': 'Rex',
    'hire': 'Ian',
    'hiring': 'Ian',
    'onboard': 'Ian',
    'agent': 'Ian',
    'hr': 'Ian',
}


def suggest_agent(project_name, description):
    """Suggest the best agent based on project type keywords."""
    text = f"{project_name} {description or ''}".lower()
    scores = {'Maya': 0, 'Sage': 0, 'Kai': 0, 'Rex': 0, 'Ian': 0}

    for keyword, agent in AGENT_TASK_MAPPING.items():
        if keyword in text:
            scores[agent] += 1

    # Return the agent with highest score, default to Maya
    if max(scores.values()) == 0:
        return 'Maya'
    return max(scores, key=scores.get)


def create_team_inbox_task(project_name, description, priority, suggested_agent, project_id=None):
    """Create a markdown file in Team Inbox for the project."""
    team_inbox_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Team Inbox')
    os.makedirs(team_inbox_path, exist_ok=True)

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_name = re.sub(r'[^\w\-]', '_', project_name)[:50]
    filename = f"{timestamp}_{safe_name}.md"
    filepath = os.path.join(team_inbox_path, filename)

    content = f"""# {project_name}

**Priority:** {priority or 'medium'}
**Suggested Agent:** {suggested_agent}
**Created:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Status:** pending
**Project ID:** {project_id or 'N/A'}

## Description

{description or 'No description provided.'}

## Task

- [ ] Review project requirements
- [ ] Confirm task assignment with orchestrator
- [ ] Begin work
- [ ] Update status to 'working'
- [ ] Deliver result to Owner Inbox

## Notes

_Agent: Add your notes here as you work._
"""

    with open(filepath, 'w') as f:
        f.write(content)

    return filepath


# ─── Agent Dispatch ───────────────────────────────────────────────────────────

AGENT_PERSONAS = {
    'Maya': """You are Maya, a pragmatic full-stack developer. You build Flask routes, SQLite schemas, and HTML/CSS templates. You write minimum working code — no overengineering, no features that weren't asked for. You match the existing code style.""",
    'Sage': """You are Sage, a thorough senior researcher. You investigate real-world skills, tools, and domain knowledge needed for a given topic. You deliver detailed, accurate findings that others can act on.""",
    'Kai': """You are Kai, a sharp marketing data scraper. You build Python scrapers using BeautifulSoup, requests, and Apify. You design clean SQLite schemas and deliver structured, deduplicated data.""",
    'Rex': """You are Rex, a practical automation engineer. You write reliable Python scripts for scheduling, monitoring, and reporting. You use cron, SQLite, and file-based pipelines. Your code runs quietly and handles errors gracefully.""",
    'Ian': """You are Ian, the HR agent. You create new agent profiles with a clear Name, Identity, and Persona. You save them to the Team folder and update the Team README.""",
}

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_DIR = os.path.dirname(os.path.abspath(__file__))


def dispatch_agent(project_id, project_name, description, priority, agent_name):
    """Spawn a claude CLI subprocess to execute the project task."""
    persona = AGENT_PERSONAS.get(agent_name, AGENT_PERSONAS['Maya'])

    prompt = f"""{persona}

You have been assigned a project by the orchestrator.

PROJECT ID: {project_id}
PROJECT NAME: {project_name}
PRIORITY: {priority}
DESCRIPTION:
{description or 'No description provided.'}

WORKSPACE: {WORKSPACE_ROOT}
APP DIR: {APP_DIR}

Do the work described above. When you are completely finished:
1. Write a brief summary of what you did to: {APP_DIR}/reports/completed_{project_id}.txt
2. Call this API to mark the project done: POST http://localhost:5000/projects/{project_id}/complete

Use curl for the API call:
  curl -s -X POST http://localhost:5000/projects/{project_id}/complete

Do not stop until the work is complete and the completion call has been made."""

    log_path = os.path.join(APP_DIR, 'reports', f'agent_log_{project_id}.txt')
    os.makedirs(os.path.join(APP_DIR, 'reports'), exist_ok=True)

    with open(log_path, 'w') as log_file:
        subprocess.Popen(
            ['claude', '--dangerously-skip-permissions', '-p', prompt],
            cwd=WORKSPACE_ROOT,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )


# ─── Projects ─────────────────────────────────────────────────────────────────

@app.route('/projects')
def projects_list():
    db = get_db()
    projects = db.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return render_template('projects/list.html', projects=projects)


@app.route('/projects/new', methods=['GET', 'POST'])
def projects_new():
    if request.method == 'POST':
        db = get_db()
        name        = request.form['name']
        description = request.form.get('description')
        priority    = request.form.get('priority', 'medium')

        db.execute(
            """INSERT INTO projects (name, description, status, priority, start_date, target_date, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, description, 'active', priority,
             request.form.get('start_date') or None,
             request.form.get('target_date') or None,
             request.form.get('tags'))
        )
        db.commit()
        project_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Pick the right agent and mark them as working
        agent_name = suggest_agent(name, description)
        agent = db.execute("SELECT id FROM agents WHERE name = ?", (agent_name,)).fetchone()
        if agent:
            db.execute(
                "UPDATE agents SET status = 'working', current_task = ? WHERE id = ?",
                (f"[Project #{project_id}] {name}", agent['id'])
            )
            db.commit()

        # Spawn the agent — fire and forget
        dispatch_agent(project_id, name, description, priority, agent_name)

        flash(f'Project #{project_id} created. {agent_name} is on it.', 'success')
        return redirect(url_for('projects_list'))
    return render_template('projects/form.html', project=None)


@app.route('/projects/<int:id>')
def projects_view(id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (id,)).fetchone()
    if project is None:
        flash('Project not found.', 'error')
        return redirect(url_for('projects_list'))
    tasks = db.execute(
        "SELECT * FROM project_tasks WHERE project_id = ? ORDER BY created_at", (id,)
    ).fetchall()
    return render_template('projects/view.html', project=project, tasks=tasks)


@app.route('/projects/<int:id>/edit', methods=['GET', 'POST'])
def projects_edit(id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (id,)).fetchone()
    if project is None:
        flash('Project not found.', 'error')
        return redirect(url_for('projects_list'))
    if request.method == 'POST':
        db.execute(
            """UPDATE projects SET name=?, description=?, status=?, priority=?,
               start_date=?, target_date=?, tags=?, updated_at=datetime('now') WHERE id=?""",
            (request.form['name'], request.form.get('description'),
             request.form.get('status', 'active'), request.form.get('priority', 'medium'),
             request.form.get('start_date') or None, request.form.get('target_date') or None,
             request.form.get('tags'), id)
        )
        db.commit()
        flash('Project updated.', 'success')
        return redirect(url_for('projects_view', id=id))
    return render_template('projects/form.html', project=project)


@app.route('/projects/<int:id>/delete', methods=['POST'])
def projects_delete(id):
    db = get_db()
    db.execute("DELETE FROM projects WHERE id = ?", (id,))
    db.commit()
    flash('Project deleted.', 'success')
    return redirect(url_for('projects_list'))


@app.route('/projects/<int:id>/complete', methods=['POST'])
def projects_complete(id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (id,)).fetchone()
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    # Mark project completed
    db.execute(
        "UPDATE projects SET status = 'completed' WHERE id = ?", (id,)
    )

    # Mark all open tasks on this project as done
    db.execute(
        "UPDATE project_tasks SET status = 'done', completed_at = datetime('now') WHERE project_id = ? AND status != 'done'",
        (id,)
    )

    # Reset the agent that was working on it back to idle
    db.execute(
        "UPDATE agents SET status = 'idle', current_task = NULL WHERE current_task LIKE ?",
        (f'[Project #{id}]%',)
    )
    db.commit()

    return jsonify({'status': 'completed', 'project_id': id})


# ─── Tasks ────────────────────────────────────────────────────────────────────

@app.route('/projects/<int:id>/tasks/new', methods=['GET', 'POST'])
def tasks_new(id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (id,)).fetchone()
    if project is None:
        flash('Project not found.', 'error')
        return redirect(url_for('projects_list'))
    if request.method == 'POST':
        status = request.form.get('status', 'todo')
        completed_at = "datetime('now')" if status == 'done' else None
        if completed_at:
            db.execute(
                """INSERT INTO project_tasks
                   (project_id, title, description, assigned_to, status, priority, due_date, completed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (id, request.form['title'], request.form.get('description'),
                 request.form.get('assigned_to'), status,
                 request.form.get('priority', 'medium'),
                 request.form.get('due_date') or None)
            )
        else:
            db.execute(
                """INSERT INTO project_tasks
                   (project_id, title, description, assigned_to, status, priority, due_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (id, request.form['title'], request.form.get('description'),
                 request.form.get('assigned_to'), status,
                 request.form.get('priority', 'medium'),
                 request.form.get('due_date') or None)
            )
        db.commit()
        flash('Task created.', 'success')
        return redirect(url_for('projects_view', id=id))
    return render_template('projects/task_form.html', project=project, task=None)


@app.route('/projects/<int:project_id>/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
def tasks_edit(project_id, task_id):
    db = get_db()
    project = db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    task = db.execute("SELECT * FROM project_tasks WHERE id = ? AND project_id = ?", (task_id, project_id)).fetchone()
    if project is None or task is None:
        flash('Not found.', 'error')
        return redirect(url_for('projects_list'))
    if request.method == 'POST':
        status = request.form.get('status', 'todo')
        if status == 'done' and task['status'] != 'done':
            db.execute(
                """UPDATE project_tasks SET title=?, description=?, assigned_to=?, status=?,
                   priority=?, due_date=?, completed_at=datetime('now') WHERE id=?""",
                (request.form['title'], request.form.get('description'),
                 request.form.get('assigned_to'), status,
                 request.form.get('priority', 'medium'),
                 request.form.get('due_date') or None, task_id)
            )
        elif status != 'done':
            db.execute(
                """UPDATE project_tasks SET title=?, description=?, assigned_to=?, status=?,
                   priority=?, due_date=?, completed_at=NULL WHERE id=?""",
                (request.form['title'], request.form.get('description'),
                 request.form.get('assigned_to'), status,
                 request.form.get('priority', 'medium'),
                 request.form.get('due_date') or None, task_id)
            )
        else:
            db.execute(
                """UPDATE project_tasks SET title=?, description=?, assigned_to=?, status=?,
                   priority=?, due_date=? WHERE id=?""",
                (request.form['title'], request.form.get('description'),
                 request.form.get('assigned_to'), status,
                 request.form.get('priority', 'medium'),
                 request.form.get('due_date') or None, task_id)
            )
        db.commit()
        flash('Task updated.', 'success')
        return redirect(url_for('projects_view', id=project_id))
    return render_template('projects/task_form.html', project=project, task=task)


@app.route('/projects/<int:project_id>/tasks/<int:task_id>/delete', methods=['POST'])
def tasks_delete(project_id, task_id):
    db = get_db()
    db.execute("DELETE FROM project_tasks WHERE id = ? AND project_id = ?", (task_id, project_id))
    db.commit()
    flash('Task deleted.', 'success')
    return redirect(url_for('projects_view', id=project_id))


# ─── Team ─────────────────────────────────────────────────────────────────────

@app.route('/agents/<int:id>/task', methods=['POST'])
def agent_task(id):
    db = get_db()
    task = request.form.get('task', '').strip()
    if task:
        db.execute("UPDATE agents SET current_task=?, status='working', updated_at=datetime('now') WHERE id=?", [task, id])
        db.commit()
        flash(f'Task sent.', 'success')
    return redirect(url_for('index'))

@app.route('/agents/<int:id>/status', methods=['POST'])
def agent_status(id):
    db = get_db()
    status = request.form.get('status', 'idle')
    task = request.form.get('current_task', '')
    db.execute("UPDATE agents SET status=?, current_task=?, updated_at=datetime('now') WHERE id=?", [status, task, id])
    db.commit()
    return redirect(url_for('index'))


# ─── RO Leads: Constants ──────────────────────────────────────────────────────

RO_SERVICE_STATES = ["DE", "FL", "GA", "MD", "NJ", "NC", "PA", "SC", "VA"]

# Zip codes grouped by state: list of (zip, city label) tuples
RO_SERVICE_ZIPCODES = {
    "DE": [("19801", "Wilmington"), ("19901", "Dover"), ("19958", "Lewes")],
    "FL": [("32202", "Jacksonville"), ("33602", "Tampa"), ("32801", "Orlando"), ("33101", "Miami"), ("32301", "Tallahassee")],
    "GA": [("30301", "Atlanta"), ("31401", "Savannah"), ("30901", "Augusta"), ("31201", "Macon")],
    "MD": [("21201", "Baltimore"), ("20850", "Rockville"), ("21701", "Frederick"), ("21401", "Annapolis"), ("20601", "Waldorf")],
    "NJ": [("08608", "Trenton"), ("07102", "Newark"), ("08401", "Atlantic City"), ("07030", "Hoboken")],
    "NC": [("27601", "Raleigh"), ("28202", "Charlotte"), ("27401", "Greensboro"), ("28801", "Asheville"), ("27701", "Durham")],
    "PA": [("19103", "Philadelphia"), ("15222", "Pittsburgh"), ("17101", "Harrisburg"), ("18503", "Scranton")],
    "SC": [("29201", "Columbia"), ("29403", "Charleston"), ("29601", "Greenville"), ("29577", "Myrtle Beach")],
    "VA": [("23219", "Richmond"), ("23451", "Virginia Beach"), ("23510", "Norfolk"), ("22314", "Alexandria"), ("20101", "Dulles"), ("24011", "Roanoke")],
}

RO_SERVICE_CITIES = [
    "Baltimore, MD", "Rockville, MD", "Frederick, MD", "Annapolis, MD",
    "Richmond, VA", "Virginia Beach, VA", "Norfolk, VA",
    "Raleigh, NC", "Charlotte, NC",
    "Philadelphia, PA", "Wilmington, DE",
    "Jacksonville, FL", "Tampa, FL", "Orlando, FL",
    "Atlanta, GA",
    "Trenton, NJ",
    "Columbia, SC", "Charleston, SC",
]

INDUSTRY_PRODUCTS = {
    "brewery": ["CO2 bulk systems", "CO2 cylinders", "Nitrogen", "Dry ice"],
    "restaurant": ["CO2 cylinders", "Dry ice"],
    "metal fabricator": ["Oxygen", "Acetylene", "Argon", "Welding supplies"],
    "laser cutting": ["Oxygen", "Nitrogen", "Laser gas delivery systems"],
    "hospital": ["Medical O2", "Medical N2", "Bulk cryogenic systems"],
    "lab": ["Specialty gases", "High-purity gases", "LN2 systems"],
    "hvac": ["Nitrogen", "Welding supplies"],
    "auto body": ["CO2", "Argon", "Welding supplies"],
    "biotech": ["Specialty gases", "LN2 systems", "Cryogenic equipment"],
    "construction": ["Oxygen", "Acetylene", "Welding supplies"],
}

CONTACT_TITLES = {
    "brewery": "Head Brewer / Operations Manager",
    "restaurant": "Owner / General Manager",
    "metal fabricator": "Plant Manager / Welding Supervisor",
    "laser cutting": "Production Manager / Engineering Manager",
    "hospital": "Materials Manager / Biomedical Engineering Director",
    "lab": "Lab Manager / Procurement Manager",
    "hvac": "Owner / Service Manager",
    "auto body": "Shop Owner / Body Shop Manager",
    "biotech": "Lab Operations Manager / Procurement Manager",
    "construction": "Project Manager / Safety Officer",
}

RO_DEFAULT_PRODUCTS = ["Compressed gases", "Welding supplies"]
RO_DEFAULT_TITLE = "Owner / Operations Manager"
RO_STATUS_OPTIONS = ["new", "contacted", "qualified", "not_a_fit"]

RO_INDUSTRIES = [
    "Brewery / Craft Beer",
    "Winery / Distillery",
    "Restaurant / Bar",
    "Coffee Shop / Cafe",
    "Food Processing / Packaging",
    "Metal Fabricator / Welding Shop",
    "Auto Body / Collision Repair",
    "Auto Repair / Mechanic Shop",
    "Laser Cutting / CNC Plasma",
    "Construction / Contractor",
    "HVAC / Plumbing / Mechanical",
    "Hospital / Medical Center",
    "Urgent Care / Clinic",
    "Dental Office",
    "Veterinary Clinic",
    "Laboratory / Research Facility",
    "Biotech / Pharmaceutical",
    "Aquarium / Fish Farm",
    "Greenhouse / Hydroponic Farm",
    "Fire Protection / Safety",
    "Industrial Manufacturing",
    "Aerospace / Defense",
    "Scuba / Dive Shop",
]


def ro_match_products(industry):
    if not industry:
        return RO_DEFAULT_PRODUCTS
    lower = industry.lower()
    for key, products in INDUSTRY_PRODUCTS.items():
        if key in lower:
            return products
    return RO_DEFAULT_PRODUCTS


def ro_match_title(industry):
    if not industry:
        return RO_DEFAULT_TITLE
    lower = industry.lower()
    for key, title in CONTACT_TITLES.items():
        if key in lower:
            return title
    return RO_DEFAULT_TITLE


# In-memory store for async search jobs: {job_id: {status, results, error, meta}}
_search_jobs = {}


def _run_search_job(job_id, business_type, area, zip_code=None, radius=None):
    """Background thread: runs Apify and stores results in _search_jobs."""
    token = os.environ.get('APIFY_TOKEN', '')
    if not token:
        _search_jobs[job_id] = {'status': 'error', 'error': 'APIFY_TOKEN not set'}
        return
    try:
        client = ApifyClient(token)
        if zip_code:
            if radius:
                search_str = f"{business_type} near {zip_code} within {radius} miles"
            else:
                search_str = f"{business_type} near {zip_code}"
        else:
            search_str = f"{business_type} in {area}"
        run_input = {
            "searchStringsArray": [search_str],
            "maxCrawledPlacesPerSearch": 100,
            "maxCrawledPlaces": 100,
            "language": "en",
            "countryCode": "us",
        }
        run = client.actor("compass/crawler-google-places").call(run_input=run_input)
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append({
                "title": item.get("title", ""),
                "url": item.get("website", ""),
                "display_url": item.get("website", ""),
                "snippet": f"{item.get('address', '')} | {item.get('phoneUnformatted', '')} | Rating: {item.get('totalScore', 'N/A')}",
                "address": item.get("address", ""),
                "phone": item.get("phoneUnformatted", ""),
                "rating": item.get("totalScore", ""),
                "category": item.get("categoryName", ""),
            })
        _search_jobs[job_id] = {
            'status': 'done',
            'results': results,
            'meta': {'business_type': business_type, 'area': area},
        }
    except Exception as e:
        _search_jobs[job_id] = {'status': 'error', 'error': str(e)}


# ─── RO Leads: Routes ─────────────────────────────────────────────────────────

@app.route('/ro/info')
def ro_info():
    return render_template('ro/info.html')


@app.route('/ro/search', methods=['GET', 'POST'])
def ro_search():
    results = None
    business_type = ""
    area = ""
    zip_code = ""
    radius = ""
    job_id = None

    if request.method == 'POST':
        business_type = request.form.get('business_type', '').strip()
        area = request.form.get('area', '').strip()
        zip_code = request.form.get('zip_code', '').strip()
        radius = request.form.get('radius', '').strip()
        if business_type and (area or zip_code):
            # Kick off background search, return immediately
            job_id = str(uuid.uuid4())
            _search_jobs[job_id] = {'status': 'running'}
            t = threading.Thread(target=_run_search_job, args=(job_id, business_type, area, zip_code, radius), daemon=True)
            t.start()
            session['search_job_id'] = job_id
            session['search_meta'] = {'business_type': business_type, 'area': area, 'zip_code': zip_code, 'radius': radius}
        else:
            flash('Please enter a business type and select an area or zip code.', 'error')

    # On GET: check if there's a running/completed job in session
    if request.method == 'GET':
        job_id = session.get('search_job_id')
        meta = session.get('search_meta', {})
        business_type = meta.get('business_type', '')
        area = meta.get('area', '')
        zip_code = meta.get('zip_code', '')
        radius = meta.get('radius', '')
        if job_id and _search_jobs.get(job_id, {}).get('status') == 'done':
            results = _search_jobs[job_id].get('results', [])
            session['last_search_results'] = results
            session['last_search_meta'] = meta
        elif not job_id:
            results = session.get('last_search_results')
            meta2 = session.get('last_search_meta', {})
            business_type = meta2.get('business_type', business_type)
            area = meta2.get('area', area)
            zip_code = meta2.get('zip_code', zip_code)
            radius = meta2.get('radius', radius)

    db = get_db()
    existing_names = {
        row[0].lower().strip()
        for row in db.execute('SELECT business_name FROM prospects').fetchall()
    }

    all_predefined_zips = [z for zips in RO_SERVICE_ZIPCODES.values() for z, _ in zips]
    return render_template(
        'ro/search.html',
        results=results,
        business_type=business_type,
        area=area,
        zip_code=zip_code,
        radius=radius,
        service_states=RO_SERVICE_STATES,
        service_cities=RO_SERVICE_CITIES,
        service_zipcodes=RO_SERVICE_ZIPCODES,
        all_predefined_zips=all_predefined_zips,
        industries=RO_INDUSTRIES,
        existing_names=existing_names,
        job_id=job_id,
        job_status=_search_jobs.get(job_id, {}).get('status') if job_id else None,
    )


@app.route('/ro/search/status/<job_id>')
def ro_search_status(job_id):
    job = _search_jobs.get(job_id, {})
    status = job.get('status', 'unknown')
    if status == 'done':
        # Persist to session so page can load results on next GET
        meta = session.get('search_meta', {})
        session['last_search_results'] = job.get('results', [])
        session['last_search_meta'] = meta
        session.pop('search_job_id', None)
    return jsonify({
        'status': status,
        'count': len(job.get('results', [])),
        'error': job.get('error'),
    })


@app.route('/ro/search/save', methods=['POST'])
def ro_save_search_result():
    business_name = request.form.get('business_name', '').strip()
    website = request.form.get('website', '').strip()
    snippet = request.form.get('snippet', '').strip()
    industry = request.form.get('industry', '').strip()
    area = request.form.get('area', '').strip()
    address = request.form.get('address', '').strip() or snippet
    phone = request.form.get('phone', '').strip()
    category = request.form.get('category', '').strip()

    if not business_name:
        flash('Business name is required.', 'error')
        return redirect(url_for('ro_search'))

    city, state = '', ''
    if ',' in area:
        parts = area.split(',', 1)
        city = parts[0].strip()
        state = parts[1].strip()
    else:
        state = area.strip()

    effective_industry = industry or category
    products = ro_match_products(effective_industry)
    title = ro_match_title(effective_industry)

    db = get_db()
    db.execute(
        """INSERT INTO prospects
           (business_name, address, phone, website, industry, city, state,
            ro_products, suggested_contact_title, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (business_name, address, phone, website, effective_industry, city, state,
         ', '.join(products), title, ''),
    )
    db.commit()
    flash(f"'{business_name}' saved to prospects.", 'success')
    return redirect(url_for('ro_search'))


@app.route('/ro/search/save-all', methods=['POST'])
def ro_save_all_results():
    """Save all results from the last search session, skipping duplicates."""
    results = session.get('last_search_results', [])
    meta = session.get('last_search_meta', {})
    industry = meta.get('business_type', '')
    area = meta.get('area', '')

    if not results:
        flash('No search results to save.', 'error')
        return redirect(url_for('ro_search'))

    city, state = '', ''
    if ',' in area:
        parts = area.split(',', 1)
        city = parts[0].strip()
        state = parts[1].strip()
    else:
        state = area.strip()

    db = get_db()
    existing = {
        row[0].lower().strip()
        for row in db.execute('SELECT business_name FROM prospects').fetchall()
    }

    saved, skipped = 0, 0
    for r in results:
        name = (r.get('title') or '').strip()
        if not name or name.lower() in existing:
            skipped += 1
            continue
        effective_industry = industry or r.get('category', '')
        products = ro_match_products(effective_industry)
        title = ro_match_title(effective_industry)
        address = r.get('address', '')
        db.execute(
            """INSERT INTO prospects
               (business_name, address, phone, website, industry, city, state,
                ro_products, suggested_contact_title, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, address, r.get('phone', ''), r.get('url', ''),
             effective_industry, city, state,
             ', '.join(products), title, ''),
        )
        existing.add(name.lower())
        saved += 1

    db.commit()
    msg = f"Saved {saved} new prospect(s)."
    if skipped:
        msg += f" Skipped {skipped} already in database."
    flash(msg, 'success')
    return redirect(url_for('ro_search'))


@app.route('/ro/profiles')
def ro_profiles():
    db = get_db()
    industry = request.args.get('industry', '')
    page = max(1, int(request.args.get('page', 1)))
    per_page = 100

    # Distinct industries for tab list
    rows = db.execute(
        "SELECT industry, COUNT(*) as cnt FROM prospects WHERE industry IS NOT NULL AND industry != '' GROUP BY industry ORDER BY cnt DESC"
    ).fetchall()
    industries = [(r['industry'], r['cnt']) for r in rows]

    # Filter + paginate
    if industry:
        total = db.execute(
            'SELECT COUNT(*) FROM prospects WHERE industry=?', (industry,)
        ).fetchone()[0]
        offset = (page - 1) * per_page
        prospects = db.execute(
            'SELECT * FROM prospects WHERE industry=? ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (industry, per_page, offset)
        ).fetchall()
    else:
        total = db.execute('SELECT COUNT(*) FROM prospects').fetchone()[0]
        offset = (page - 1) * per_page
        prospects = db.execute(
            'SELECT * FROM prospects ORDER BY created_at DESC LIMIT ? OFFSET ?',
            (per_page, offset)
        ).fetchall()

    total_pages = max(1, (total + per_page - 1) // per_page)

    return render_template(
        'ro/profiles.html',
        prospects=prospects,
        industries=industries,
        current_industry=industry,
        current_page=page,
        total_pages=total_pages,
        total=total,
    )


@app.route('/ro/profiles/add', methods=['GET', 'POST'])
def ro_profile_add():
    if request.method == 'POST':
        f = request.form
        industry = f.get('industry', '')
        products = f.get('ro_products') or ', '.join(ro_match_products(industry))
        contact_title = f.get('suggested_contact_title') or ro_match_title(industry)
        db = get_db()
        db.execute(
            """INSERT INTO prospects
               (business_name, address, phone, website, industry, city, state,
                ro_products, suggested_contact_title, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (f.get('business_name'), f.get('address'), f.get('phone'),
             f.get('website'), industry, f.get('city'), f.get('state'),
             products, contact_title, f.get('status', 'new'), f.get('notes')),
        )
        db.commit()
        flash('Prospect added.', 'success')
        return redirect(url_for('ro_profiles'))
    return render_template(
        'ro/profile_add.html',
        status_options=RO_STATUS_OPTIONS,
        service_states=RO_SERVICE_STATES,
    )


@app.route('/ro/profiles/<int:prospect_id>')
def ro_profile_view(prospect_id):
    db = get_db()
    prospect = db.execute(
        'SELECT * FROM prospects WHERE id = ?', (prospect_id,)
    ).fetchone()
    if not prospect:
        flash('Prospect not found.', 'error')
        return redirect(url_for('ro_profiles'))
    contacts = db.execute(
        'SELECT * FROM ro_contacts WHERE prospect_id = ? ORDER BY name', (prospect_id,)
    ).fetchall()
    return render_template(
        'ro/profile_view.html',
        prospect=prospect,
        contacts=contacts,
        status_options=RO_STATUS_OPTIONS,
    )


@app.route('/ro/profiles/<int:prospect_id>/edit', methods=['POST'])
def ro_profile_edit(prospect_id):
    f = request.form
    db = get_db()
    db.execute(
        """UPDATE prospects SET
           business_name=?, address=?, phone=?, website=?, industry=?,
           city=?, state=?, ro_products=?, suggested_contact_title=?,
           status=?, notes=?, updated_at=datetime('now')
           WHERE id=?""",
        (f.get('business_name'), f.get('address'), f.get('phone'),
         f.get('website'), f.get('industry'), f.get('city'), f.get('state'),
         f.get('ro_products'), f.get('suggested_contact_title'),
         f.get('status'), f.get('notes'), prospect_id),
    )
    db.commit()
    flash('Prospect updated.', 'success')
    return redirect(url_for('ro_profile_view', prospect_id=prospect_id))


@app.route('/ro/profiles/<int:prospect_id>/delete', methods=['POST'])
def ro_profile_delete(prospect_id):
    db = get_db()
    db.execute('DELETE FROM prospects WHERE id = ?', (prospect_id,))
    db.commit()
    flash('Prospect deleted.', 'success')
    return redirect(url_for('ro_profiles'))


@app.route('/ro/contacts')
def ro_contacts():
    db = get_db()
    rows = db.execute(
        """SELECT c.*, p.business_name
           FROM ro_contacts c
           LEFT JOIN prospects p ON c.prospect_id = p.id
           ORDER BY c.name"""
    ).fetchall()
    return render_template('ro/contacts.html', contacts=rows)


@app.route('/ro/contacts/add', methods=['GET', 'POST'])
def ro_contact_add():
    db = get_db()
    if request.method == 'POST':
        f = request.form
        db.execute(
            """INSERT INTO ro_contacts
               (prospect_id, name, title, email, phone, linkedin_url, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (f.get('prospect_id') or None, f.get('name'), f.get('title'),
             f.get('email'), f.get('phone'), f.get('linkedin_url'), f.get('notes')),
        )
        db.commit()
        flash('Contact added.', 'success')
        return redirect(url_for('ro_contacts'))
    prospects = db.execute(
        'SELECT id, business_name FROM prospects ORDER BY business_name'
    ).fetchall()
    return render_template('ro/contact_add.html', prospects=prospects)


@app.route('/ro/contacts/<int:contact_id>/edit', methods=['GET', 'POST'])
def ro_contact_edit(contact_id):
    db = get_db()
    contact = db.execute(
        'SELECT * FROM ro_contacts WHERE id = ?', (contact_id,)
    ).fetchone()
    if not contact:
        flash('Contact not found.', 'error')
        return redirect(url_for('ro_contacts'))
    if request.method == 'POST':
        f = request.form
        db.execute(
            """UPDATE ro_contacts SET
               prospect_id=?, name=?, title=?, email=?, phone=?,
               linkedin_url=?, notes=? WHERE id=?""",
            (f.get('prospect_id') or None, f.get('name'), f.get('title'),
             f.get('email'), f.get('phone'), f.get('linkedin_url'),
             f.get('notes'), contact_id),
        )
        db.commit()
        flash('Contact updated.', 'success')
        return redirect(url_for('ro_contacts'))
    prospects = db.execute(
        'SELECT id, business_name FROM prospects ORDER BY business_name'
    ).fetchall()
    return render_template('ro/contact_edit.html', contact=contact, prospects=prospects)


@app.route('/ro/contacts/<int:contact_id>/delete', methods=['POST'])
def ro_contact_delete(contact_id):
    db = get_db()
    db.execute('DELETE FROM ro_contacts WHERE id = ?', (contact_id,))
    db.commit()
    flash('Contact deleted.', 'success')
    return redirect(url_for('ro_contacts'))


@app.route('/ro/pipeline')
def ro_pipeline():
    db = get_db()
    all_prospects = db.execute(
        'SELECT * FROM prospects ORDER BY updated_at DESC'
    ).fetchall()
    columns = {'new': [], 'contacted': [], 'qualified': [], 'not_a_fit': []}
    for p in all_prospects:
        status = p['status'] if p['status'] in columns else 'new'
        columns[status].append(p)
    return render_template('ro/pipeline.html', columns=columns)


@app.route('/ro/pipeline/move/<int:prospect_id>', methods=['POST'])
def ro_pipeline_move(prospect_id):
    new_status = request.form.get('status')
    if new_status not in RO_STATUS_OPTIONS:
        flash('Invalid status.', 'error')
        return redirect(url_for('ro_pipeline'))
    db = get_db()
    db.execute(
        "UPDATE prospects SET status=?, updated_at=datetime('now') WHERE id=?",
        (new_status, prospect_id),
    )
    db.commit()
    return redirect(url_for('ro_pipeline'))


# ─── Contact Scraping ─────────────────────────────────────────────────────────

SKIP_PREFIXES = ['noreply', 'no-reply', 'donotreply', 'test@', 'example', 'webmaster', 'postmaster', 'bounce', 'abuse']
GENERIC_PREFIXES = ['info@', 'contact@', 'hello@', 'sales@', 'office@', 'mail@', 'admin@', 'support@', 'inquiry@', 'inquiries@']

def scrape_emails_from_url(url, timeout=8):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (compatible; ROLeadBot/1.0)'}
        r = http_requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        raw = re.findall(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', r.text)
        seen = set()
        unique = []
        for e in raw:
            e = e.lower()
            if e not in seen:
                seen.add(e)
                unique.append(e)
        return unique
    except Exception:
        return []


def find_best_contacts(website_url):
    """Scrape website for emails, return up to 2 best contacts."""
    if not website_url:
        return []
    base = website_url.rstrip('/')
    pages_to_try = [base, base + '/contact', base + '/contact-us', base + '/about', base + '/team']
    all_emails = []
    seen = set()
    for url in pages_to_try[:4]:
        for e in scrape_emails_from_url(url):
            if e not in seen:
                seen.add(e)
                all_emails.append(e)

    # Filter junk
    filtered = [e for e in all_emails if not any(e.startswith(s) or s in e for s in SKIP_PREFIXES)]
    # Rank: named emails first, generic second
    named   = [e for e in filtered if not any(e.startswith(g) for g in GENERIC_PREFIXES)]
    generic = [e for e in filtered if any(e.startswith(g) for g in GENERIC_PREFIXES)]
    ranked  = named + generic
    return ranked[:2]


def find_with_hunter(website_url):
    """Query Hunter.io domain search. Returns list of dicts with email, name, title."""
    api_key = os.environ.get('HUNTER_API_KEY', '')
    if not api_key:
        return []
    try:
        from urllib.parse import urlparse
        domain = urlparse(website_url).netloc or urlparse('https://' + website_url).netloc
        domain = domain.lstrip('www.')
        r = http_requests.get(
            'https://api.hunter.io/v2/domain-search',
            params={'domain': domain, 'api_key': api_key, 'limit': 5},
            timeout=10
        )
        if r.status_code != 200:
            return []
        data = r.json().get('data', {})
        contacts = []
        for e in data.get('emails', []):
            if e.get('value'):
                contacts.append({
                    'email': e['value'].lower(),
                    'name': ' '.join(filter(None, [e.get('first_name', ''), e.get('last_name', '')])),
                    'title': e.get('position', '')
                })
        # Rank: named personal emails first
        named   = [c for c in contacts if c['name']]
        generic = [c for c in contacts if not c['name']]
        return (named + generic)[:3]
    except Exception:
        return []


def hunter_verify_email(email):
    """Verify a single email via Hunter.io. Returns {status, score}."""
    api_key = os.environ.get('HUNTER_API_KEY', '')
    if not api_key:
        return {'status': 'unknown', 'score': 0}
    try:
        r = http_requests.get(
            'https://api.hunter.io/v2/email-verifier',
            params={'email': email, 'api_key': api_key},
            timeout=15
        )
        if r.status_code != 200:
            return {'status': 'unknown', 'score': 0}
        data = r.json().get('data', {})
        return {
            'status': data.get('status', 'unknown'),
            'score': data.get('score', 0),
        }
    except Exception:
        return {'status': 'unknown', 'score': 0}


def hunter_find_email(first_name, last_name, domain):
    """Find a person's email via Hunter.io Email Finder. Returns {email, confidence} or None."""
    api_key = os.environ.get('HUNTER_API_KEY', '')
    if not api_key or not first_name or not domain:
        return None
    try:
        r = http_requests.get(
            'https://api.hunter.io/v2/email-finder',
            params={
                'domain': domain,
                'first_name': first_name,
                'last_name': last_name or '',
                'api_key': api_key,
            },
            timeout=15
        )
        if r.status_code != 200:
            return None
        data = r.json().get('data', {})
        email = data.get('email')
        if not email:
            return None
        return {'email': email.lower(), 'confidence': data.get('score', 0)}
    except Exception:
        return None


def hunter_discover(keywords, location, limit=10):
    """Discover companies via Hunter.io. Returns list of {name, domain, website, industry, size}."""
    api_key = os.environ.get('HUNTER_API_KEY', '')
    if not api_key or not keywords:
        return []
    try:
        r = http_requests.get(
            'https://api.hunter.io/v2/companies/search',
            params={
                'keywords': keywords,
                'location': location or '',
                'limit': limit,
                'api_key': api_key,
            },
            timeout=15
        )
        if r.status_code != 200:
            return []
        companies = r.json().get('data', {}).get('companies', [])
        results = []
        for c in companies:
            domain = c.get('domain', '')
            results.append({
                'name': c.get('name', ''),
                'domain': domain,
                'website': f'https://{domain}' if domain else '',
                'industry': c.get('industry', ''),
                'size': c.get('size', ''),
                'hunter_only': True,
                'hunter_enriched': False,
            })
        return results
    except Exception:
        return []


_hunter_account_cache = {'data': None, 'at': 0}

def hunter_account_info():
    """Return Hunter.io account usage. Cached for 5 minutes."""
    import time
    now = time.time()
    if _hunter_account_cache['data'] and now - _hunter_account_cache['at'] < 300:
        return _hunter_account_cache['data']
    api_key = os.environ.get('HUNTER_API_KEY', '')
    empty = {'searches_used': 0, 'searches_left': 0, 'verifications_used': 0, 'verifications_left': 0}
    if not api_key:
        return empty
    try:
        r = http_requests.get(
            'https://api.hunter.io/v2/account',
            params={'api_key': api_key},
            timeout=10
        )
        if r.status_code != 200:
            return empty
        d = r.json().get('data', {})
        requests_data = d.get('requests', {})
        searches = requests_data.get('searches', {})
        verifications = requests_data.get('verifications', {})
        result = {
            'searches_used': searches.get('used', 0),
            'searches_left': searches.get('available', 0),
            'verifications_used': verifications.get('used', 0),
            'verifications_left': verifications.get('available', 0),
        }
        _hunter_account_cache['data'] = result
        _hunter_account_cache['at'] = now
        return result
    except Exception:
        return empty


def get_mx_host(domain):
    """Return the highest-priority MX hostname for a domain, or None."""
    try:
        import dns.resolver
        records = dns.resolver.resolve(domain, 'MX')
        return str(sorted(records, key=lambda r: r.preference)[0].exchange).rstrip('.')
    except Exception:
        return None


def smtp_verify(email, mx_host):
    """SMTP handshake check — returns True if server accepts the address."""
    try:
        with smtplib.SMTP(timeout=8) as s:
            s.connect(mx_host, 25)
            s.ehlo('robertsoxygen.com')
            s.mail('verify@robertsoxygen.com')
            code, _ = s.rcpt(email)
            s.quit()
            return code == 250
    except Exception:
        return False


def guess_emails(domain, mx_host):
    """
    Try common generic formats against the domain.
    Verifies each via SMTP handshake. Returns up to 3 verified addresses.
    Falls back to returning unverified generics if SMTP is blocked.
    """
    candidates = [
        f'info@{domain}',
        f'sales@{domain}',
        f'contact@{domain}',
        f'hello@{domain}',
        f'office@{domain}',
        f'inquiries@{domain}',
    ]
    if not mx_host:
        return []

    verified = []
    smtp_blocked = False
    for email in candidates:
        result = smtp_verify(email, mx_host)
        if result:
            verified.append({'email': email, 'name': '', 'title': ''})
            if len(verified) >= 3:
                break
        elif not verified and not smtp_blocked:
            # If we get no 250s at all after first 2 tries, server likely blocks probing
            smtp_blocked = True

    # If SMTP is blocked (catch-all or firewall), return top generic unverified
    if not verified and smtp_blocked:
        return [{'email': candidates[0], 'name': '', 'title': ''}]

    return verified


@app.route('/ro/profiles/<int:prospect_id>/deep-profile', methods=['POST'])
def ro_deep_profile(prospect_id):
    """Use Firecrawl to extract structured data from the prospect's website and fill empty fields."""
    db = get_db()
    prospect = db.execute('SELECT * FROM prospects WHERE id = ?', (prospect_id,)).fetchone()
    if not prospect:
        return jsonify({'error': 'Prospect not found'}), 404
    if not prospect['website']:
        return jsonify({'error': 'No website on file for this prospect'}), 400
    if not os.environ.get('FIRECRAWL_API_KEY'):
        return jsonify({'error': 'FIRECRAWL_API_KEY not configured'}), 500

    from firecrawl_client import profile_prospect
    extracted = profile_prospect(prospect['website'])

    if 'error' in extracted:
        return jsonify({'error': extracted['error']}), 500

    # Map Firecrawl fields → DB columns, only fill if currently empty
    field_map = {
        'phone':               'phone',
        'address':             'address',
        'city':                'city',
        'state':               'state',
        'business_type':       'industry',
        'gas_signals':         None,   # goes into notes
        'equipment_mentioned': None,   # goes into notes
        'current_supplier':    None,   # goes into notes
    }

    updates = {}
    notes_additions = []

    for fc_field, db_col in field_map.items():
        val = extracted.get(fc_field, '').strip()
        if not val:
            continue
        if db_col and not prospect[db_col]:
            updates[db_col] = val
        elif fc_field in ('gas_signals', 'equipment_mentioned', 'current_supplier'):
            notes_additions.append(f'{fc_field.replace("_", " ").title()}: {val}')

    # Append gas intelligence to notes
    if notes_additions:
        existing_notes = prospect['notes'] or ''
        separator = '\n\n' if existing_notes else ''
        new_notes = existing_notes + separator + '[Firecrawl]\n' + '\n'.join(notes_additions)
        updates['notes'] = new_notes

    # Save extracted contact person to ro_contacts if found and not duplicate
    contact_name  = extracted.get('contact_name', '').strip()
    contact_title = extracted.get('contact_title', '').strip()
    saved_contact = None
    if contact_name:
        existing = db.execute(
            'SELECT id FROM ro_contacts WHERE prospect_id=? AND name=?',
            (prospect_id, contact_name)
        ).fetchone()
        if not existing:
            db.execute(
                'INSERT INTO ro_contacts (prospect_id, name, title, is_suggested) VALUES (?, ?, ?, 1)',
                (prospect_id, contact_name, contact_title)
            )
            db.commit()
            saved_contact = {'name': contact_name, 'title': contact_title}

    if updates:
        set_clause = ', '.join(f'{col} = ?' for col in updates)
        db.execute(
            f'UPDATE prospects SET {set_clause} WHERE id = ?',
            list(updates.values()) + [prospect_id]
        )
        db.commit()

    return jsonify({
        'updated_fields': list(updates.keys()),
        'saved_contact':  saved_contact,
        'raw':            extracted,
    })


@app.route('/ro/profiles/<int:prospect_id>/find-contacts', methods=['POST'])
def ro_find_contacts(prospect_id):
    db = get_db()
    prospect = db.execute('SELECT * FROM prospects WHERE id = ?', (prospect_id,)).fetchone()
    if not prospect:
        return jsonify({'error': 'Prospect not found'}), 404
    if not prospect['website']:
        return jsonify({'error': 'No website on file for this prospect'}), 400

    # 1. Hunter.io
    raw_contacts = find_with_hunter(prospect['website'])
    source = 'hunter'

    # 2. Website scraper
    if not raw_contacts:
        emails = find_best_contacts(prospect['website'])
        raw_contacts = [{'email': e, 'name': '', 'title': ''} for e in emails]
        source = 'scrape'

    # 3. Email format guesser + SMTP verification
    if not raw_contacts:
        from urllib.parse import urlparse
        parsed = urlparse(prospect['website'])
        domain = (parsed.netloc or parsed.path).lstrip('www.')
        mx_host = get_mx_host(domain)
        raw_contacts = guess_emails(domain, mx_host)
        source = 'guess'

    if not raw_contacts:
        return jsonify({'error': 'No email addresses found'}), 404

    saved = []
    for c in raw_contacts:
        email = c['email']
        existing = db.execute('SELECT id FROM ro_contacts WHERE prospect_id=? AND email=?', (prospect_id, email)).fetchone()
        if not existing:
            db.execute(
                'INSERT INTO ro_contacts (prospect_id, name, title, email, is_suggested) VALUES (?, ?, ?, ?, 1)',
                (prospect_id, c['name'], c['title'], email)
            )
            db.commit()
        contact = db.execute('SELECT * FROM ro_contacts WHERE prospect_id=? AND email=?', (prospect_id, email)).fetchone()
        saved.append({'id': contact['id'], 'email': email, 'name': contact['name'] or '', 'title': contact['title'] or ''})

    return jsonify({'contacts': saved, 'source': source})


@app.route('/ro/contacts/<int:contact_id>/draft-email', methods=['POST'])
def ro_draft_email(contact_id):
    db = get_db()
    contact = db.execute('SELECT * FROM ro_contacts WHERE id = ?', (contact_id,)).fetchone()
    if not contact:
        return jsonify({'error': 'Contact not found'}), 404
    prospect = db.execute('SELECT * FROM prospects WHERE id = ?', (contact['prospect_id'],)).fetchone()
    if not prospect:
        return jsonify({'error': 'Prospect not found'}), 404

    data = request.get_json(silent=True) or {}
    model_key = data.get('model', 'claude')

    contact_name = contact['name'] or 'there'
    contact_title = contact['title'] or 'decision maker'

    prompt = f"""Write a concise, professional cold outreach email from Roberts Oxygen to a prospect.

Roberts Oxygen is an industrial gas supplier (oxygen, CO2, nitrogen, welding gases, and related products) serving businesses across MD, VA, DC, PA, DE, NJ, NC, SC, GA, and FL — including locations in Jacksonville, Tampa, and Orlando.

Prospect details:
- Business: {prospect['business_name']}
- Industry: {prospect['industry'] or 'unknown'}
- Location: {prospect['city'] or ''} {prospect['state'] or ''}
- Likely products they need: {prospect['ro_products'] or 'to be determined'}
- Contact name: {contact_name}
- Contact title: {contact_title}

Write a short (3-4 paragraph) outreach email:
1. Subject line (on its own line starting with "Subject:")
2. Opening that references their specific industry/business
3. Brief value prop from Roberts Oxygen relevant to their industry
4. Soft call to action (quick call or visit)

Keep it warm, direct, and under 200 words. No fluff."""

    try:
        client, model_id = get_ai_client(model_key)
        response = client.messages.create(
            model=model_id,
            max_tokens=512,
            messages=[{'role': 'user', 'content': prompt}]
        )
        draft = next((b.text for b in response.content if hasattr(b, 'text')), '')
        return jsonify({'draft': draft, 'model': model_key})
    except anthropic.BadRequestError as e:
        return jsonify({'error': str(e)}), 402
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─── Competitor Profiles ──────────────────────────────────────────────────────

@app.route('/competitors')
def competitors():
    import json as _json
    snapshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'competitor_snapshots')
    competitors_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'competitors.json')

    with open(competitors_file) as f:
        comp_list = _json.load(f)['competitors']

    cards = []
    for comp in comp_list:
        name = comp['name']
        prefix = name.lower().replace(' ', '_')
        # Find most recent snapshot
        try:
            files = sorted([
                fn for fn in os.listdir(snapshots_dir)
                if fn.startswith(prefix) and fn.endswith('.json')
            ])
        except FileNotFoundError:
            files = []

        if files:
            with open(os.path.join(snapshots_dir, files[-1])) as f:
                data = _json.load(f)
            snapshot_date = files[-1].replace(prefix + '_', '').replace('.json', '')
            # Format date
            try:
                snapshot_date = datetime.datetime.strptime(snapshot_date, '%Y%m%d').strftime('%b %d, %Y')
            except Exception:
                pass
        else:
            data = {}
            snapshot_date = None

        cards.append({
            'name': name,
            'url': comp['url'],
            'notes': comp.get('notes', ''),
            'snapshot_date': snapshot_date,
            'data': data,
        })

    return render_template('competitors.html', cards=cards)


@app.route('/competitors/run-scan', methods=['POST'])
def competitors_run_scan():
    """Trigger a competitor monitor scan in the background."""
    import subprocess
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'competitor_monitor.py')
    subprocess.Popen(
        ['python3', script],
        stdout=open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports', 'competitor_scan.log'), 'w'),
        stderr=subprocess.STDOUT,
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    flash('Competitor scan started — check back in a few minutes.', 'success')
    return redirect(url_for('competitors'))


AVAILABLE_MODELS = {
    'claude':  {'label': 'Claude Sonnet',    'model': 'claude-sonnet-4-6',  'provider': 'anthropic'},
    'minimax': {'label': 'MiniMax M2.7',     'model': 'MiniMax-M2.7',       'provider': 'minimax'},
}


def get_ai_client(model_key='claude'):
    """Return (anthropic_client, model_id) for the given model key."""
    cfg = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS['claude'])
    if cfg['provider'] == 'minimax':
        key = os.environ.get('MINIMAX_API_KEY', '')
        client = anthropic.Anthropic(api_key=key, base_url='https://api.minimax.io/anthropic')
    else:
        key = os.environ.get('ANTHROPIC_API_KEY', '')
        client = anthropic.Anthropic(api_key=key)
    return client, cfg['model']


CHAT_SYSTEM_PROMPT = """You are the orchestrator for Roberts Oxygen's marketing tools team.
Roberts Oxygen is an industrial gas company (oxygen, CO2, nitrogen, and related products) serving businesses across the mid-Atlantic US.

Your AI team:
- Sage (Senior Researcher): researches roles, markets, and requirements
- Ian (HR Agent): hires and defines new agents
- Maya (Full-Stack Developer): builds Flask web apps and UI
- Rex (Automation Engineer): scheduled scripts, Discord monitor, background automation
- Kai (Marketing Data Scraper): Apify scraping, prospect database, data pipelines

You are talking directly with the business owner through the dashboard chat. Be concise, direct, and helpful. You can discuss projects, team tasks, strategy, and any business needs."""

# In-memory message queue for bridge
message_queue = []
bridge_sid = None  # Socket ID of connected bridge

# ─── Chat Bridge: Dashboard ↔ Orchestrator ────────────────────────────────────

@app.route('/chat/send', methods=['POST'])
def chat_send():
    """Receive message from dashboard, store in DB for orchestrator polling."""
    data = request.get_json()
    content = data.get('message', '').strip()
    if not content:
        return jsonify({'error': 'No message provided'}), 400

    db = get_db()
    db.execute(
        "INSERT INTO chat_messages (direction, content, sender, read) VALUES ('in', ?, 'user', 0)",
        (content,)
    )
    db.commit()
    return jsonify({'status': 'sent', 'message': 'Message queued for orchestrator'})


@app.route('/chat/poll', methods=['GET'])
def chat_poll():
    """Dashboard polls for new responses from orchestrator."""
    db = get_db()
    # Get unread outgoing messages (from orchestrator)
    rows = db.execute(
        "SELECT id, content, sender, created_at FROM chat_messages WHERE direction = 'out' AND read = 0 ORDER BY created_at ASC"
    ).fetchall()

    messages = []
    for row in rows:
        messages.append({
            'id': row['id'],
            'content': row['content'],
            'sender': row['sender'],
            'created_at': row['created_at']
        })
        # Mark as read
        db.execute("UPDATE chat_messages SET read = 1 WHERE id = ?", (row['id'],))

    db.commit()
    return jsonify({'messages': messages})


@app.route('/chat/history', methods=['GET'])
def chat_history():
    """Get full chat history (for page load)."""
    db = get_db()
    rows = db.execute(
        "SELECT content, sender, created_at FROM chat_messages ORDER BY created_at ASC LIMIT 50"
    ).fetchall()
    return jsonify({'messages': [{'content': r['content'], 'sender': r['sender'], 'created_at': r['created_at']} for r in rows]})


# Legacy chat endpoint (for Anthropic API fallback)
@app.route('/chat', methods=['POST'])
def chat():
    """Direct chat via Anthropic API (fallback when orchestrator offline)."""
    data = request.get_json()
    messages = data.get('messages', [])
    if not messages:
        return jsonify({'error': 'No messages provided'}), 400

    model_key = data.get('model', 'claude')
    client, model_id = get_ai_client(model_key)
    try:
        response = client.messages.create(
            model=model_id,
            max_tokens=1024,
            system=CHAT_SYSTEM_PROMPT,
            messages=messages
        )
        text = next((b.text for b in response.content if hasattr(b, 'text')), '')
        return jsonify({'response': text, 'model': model_key})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@socketio.on('connect')
def handle_connect():
    """Handle client connections."""
    pass


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnections."""
    global bridge_sid
    if request.sid == bridge_sid:
        bridge_sid = None
        socketio.emit('bridge_status', {'connected': False, 'queued': len(message_queue)})


@socketio.on('bridge_register')
def handle_bridge_register():
    """Terminal bridge registers itself."""
    global bridge_sid
    bridge_sid = request.sid
    emit('bridge_connected', {'status': 'connected', 'queued': len(message_queue)})
    socketio.emit('bridge_status', {'connected': True, 'queued': 0})

    # Send any queued messages
    while message_queue:
        msg = message_queue.pop(0)
        socketio.emit('chat_message', msg, to=bridge_sid)


@socketio.on('chat_message')
def handle_chat_message(data):
    """Receive message from web dashboard and forward to bridge."""
    if bridge_sid:
        socketio.emit('chat_message', data, to=bridge_sid)
    else:
        message_queue.append(data)
        socketio.emit('bridge_status', {'connected': False, 'queued': len(message_queue)})


@socketio.on('chat_response')
def handle_chat_response(data):
    """Receive response from bridge and broadcast to all clients."""
    socketio.emit('chat_response', data)


if __name__ == '__main__':
    with app.app_context():
        init_db()
    socketio.run(app, debug=True, port=5000, allow_unsafe_werkzeug=True)
