# Dark Forest UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing light-green top-nav UI with the approved Dark Forest design: hunter green dominant, dark backgrounds, sidebar nav, lighter text, larger typography, and 5 CSS-only animations.

**Architecture:** Full replacement of `static/style.css` + structural update to `base.html` (top-nav → sidebar). All 32 templates inherit the new look via CSS; only `index.html`, `lock.html`, and `base.html` need structural HTML changes.

**Tech Stack:** Flask/Jinja2, vanilla CSS (no new dependencies), no JS libraries

---

## File Map

| File | Change |
|---|---|
| `Owner Inbox/static/style.css` | Full replacement |
| `Owner Inbox/templates/base.html` | Top-nav → sidebar layout shell |
| `Owner Inbox/templates/index.html` | Add particle divs + count-in class |
| `Owner Inbox/templates/lock.html` | Update inline styles to Dark Forest |
| All other templates | No HTML changes — inherit from base + style.css |

---

## Task 1: Replace `style.css`

**Files:**
- Replace: `Owner Inbox/static/style.css`

- [ ] **Step 1: Back up the existing CSS**

```bash
cp "Owner Inbox/static/style.css" "Owner Inbox/static/style.css.bak"
```

- [ ] **Step 2: Write the new `style.css`**

Replace the entire file with:

```css
/* ============================================================
   RO Marketing Tools — Dark Forest Design System
   ============================================================ */

:root {
  --bg-page:       #0c1a10;
  --bg-chrome:     #070f09;
  --green-primary: #1a5c35;
  --green-glow:    #2ecc71;
  --bg-card:       rgba(255, 255, 255, 0.05);
  --border:        #1a3a20;
  --text-heading:  #f0fff4;
  --text-body:     #c8e6ce;
  --text-label:    #6db87e;
  --text-muted:    #5a8a6a;
  --danger:        #e05555;
  --warning:       #e8a020;
  --radius-sm:     6px;
  --radius:        10px;
  --radius-lg:     14px;
  --transition:    all 0.2s ease;
  --sidebar-width: 200px;
}

/* ── Reset ── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Segoe UI', system-ui, Arial, sans-serif;
  background: var(--bg-page);
  color: var(--text-body);
  font-size: 0.72rem;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  min-height: 100vh;
}

a { color: var(--green-glow); text-decoration: none; transition: var(--transition); }
a:hover { color: var(--text-heading); }

/* ============================================================
   App Shell — Sidebar + Main
   ============================================================ */

.app-shell {
  display: flex;
  min-height: 100vh;
}

/* ── Sidebar ── */
.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-chrome);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 200;
  overflow-y: auto;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 16px 16px;
  border-bottom: 1px solid var(--border);
  text-decoration: none;
}

.sidebar-logo-mark {
  width: 36px;
  height: 36px;
  background: var(--green-primary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--text-heading);
  flex-shrink: 0;
  box-shadow: 0 0 12px rgba(26, 92, 53, 0.5);
}

.sidebar-logo-text {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-heading);
  letter-spacing: 0.03em;
  line-height: 1.2;
}

.sidebar-logo-text small {
  display: block;
  font-size: 0.6rem;
  color: var(--text-muted);
  font-weight: 400;
}

.sidebar-nav {
  padding: 12px 0;
  flex: 1;
}

.sidebar-section-label {
  font-size: 0.58rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 10px 16px 4px;
}

.sidebar-nav a {
  display: block;
  padding: 7px 16px;
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--text-muted);
  letter-spacing: 0.02em;
  transition: var(--transition);
  border-left: 2px solid transparent;
}

.sidebar-nav a:hover {
  color: var(--text-body);
  background: rgba(255, 255, 255, 0.03);
  border-left-color: var(--border);
}

.sidebar-nav a.active {
  color: var(--text-heading);
  background: rgba(26, 92, 53, 0.25);
  border-left-color: var(--green-glow);
  font-weight: 600;
}

/* ── Main content ── */
.main-content {
  margin-left: var(--sidebar-width);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-chrome);
  position: sticky;
  top: 0;
  z-index: 100;
}

.topbar h1,
.page-title {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-heading);
  letter-spacing: -0.01em;
}

.page-body {
  padding: 24px;
  flex: 1;
}

/* ── Mobile hamburger ── */
.hamburger {
  display: none;
  background: none;
  border: none;
  color: var(--text-body);
  font-size: 1.4rem;
  cursor: pointer;
  padding: 4px 8px;
  line-height: 1;
}

.sidebar-overlay {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  z-index: 199;
}

/* ── Legacy .container support (fallback) ── */
.container {
  padding: 24px;
}

/* ============================================================
   Flash messages
   ============================================================ */

.flash {
  padding: 10px 16px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  margin-bottom: 16px;
  border: 1px solid var(--border);
}

.flash-success { background: rgba(26, 92, 53, 0.25); color: var(--green-glow); border-color: var(--green-primary); }
.flash-error   { background: rgba(224, 85, 85, 0.15); color: #f08080; border-color: var(--danger); }
.flash-warning { background: rgba(232, 160, 32, 0.15); color: var(--warning); border-color: var(--warning); }
.flash-info    { background: rgba(255, 255, 255, 0.05); color: var(--text-body); border-color: var(--border); }

/* ============================================================
   Page headers
   ============================================================ */

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  gap: 12px;
  flex-wrap: wrap;
}

.page-header h1 {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-heading);
  letter-spacing: -0.01em;
}

.section-title {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-label);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 20px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
  position: relative;
}

.section-title::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 40px;
  height: 1px;
  background: var(--green-glow);
  animation: glow-scan 2.5s linear infinite;
}

/* ============================================================
   Stat Grid (Dashboard)
   ============================================================ */

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  position: relative;
  overflow: hidden;
}

/* Shimmer on top edge */
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--green-glow), transparent);
  animation: shimmer 3s ease-in-out infinite;
}

.stat-card:nth-child(2)::before { animation-delay: 0.4s; }
.stat-card:nth-child(3)::before { animation-delay: 0.8s; }
.stat-card:nth-child(4)::before { animation-delay: 1.2s; }
.stat-card:nth-child(5)::before { animation-delay: 1.6s; }
.stat-card:nth-child(6)::before { animation-delay: 2.0s; }
.stat-card:nth-child(7)::before { animation-delay: 2.4s; }
.stat-card:nth-child(8)::before { animation-delay: 0.2s; }
.stat-card:nth-child(9)::before { animation-delay: 0.6s; }

.stat-card .count {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text-heading);
  line-height: 1.2;
  animation: count-in 0.5s ease-out both;
}

.stat-card .label {
  font-size: 0.62rem;
  font-weight: 700;
  color: var(--text-label);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-top: 4px;
}

/* ============================================================
   Cards (generic)
   ============================================================ */

.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-heading);
}

/* ============================================================
   Agent Cards
   ============================================================ */

.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}

.agent-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.agent-card h2 {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--text-heading);
}

.agent-role {
  font-size: 0.65rem;
  color: var(--text-label);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.current-task {
  font-size: 0.7rem;
  color: var(--text-body);
  background: rgba(26, 92, 53, 0.15);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
}

/* ============================================================
   Badges / Status
   ============================================================ */

.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 0.6rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.badge-idle, .badge-active {
  background: rgba(26, 92, 53, 0.3);
  color: var(--green-glow);
  border: 1px solid var(--green-primary);
  animation: pulse-glow 2s ease-in-out infinite;
}

.badge-working {
  background: rgba(232, 160, 32, 0.2);
  color: var(--warning);
  border: 1px solid var(--warning);
}

.badge-error {
  background: rgba(224, 85, 85, 0.2);
  color: #f08080;
  border: 1px solid var(--danger);
}

/* ============================================================
   Buttons
   ============================================================ */

.btn, button[type=submit], input[type=submit] {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 0.72rem;
  font-weight: 600;
  cursor: pointer;
  transition: var(--transition);
  border: 1px solid transparent;
  text-decoration: none;
  line-height: 1;
}

.btn-primary, button[type=submit], input[type=submit] {
  background: var(--green-primary);
  color: var(--text-heading);
  border-color: var(--green-primary);
}

.btn-primary:hover, button[type=submit]:hover, input[type=submit]:hover {
  background: #225f3a;
  color: var(--text-heading);
  box-shadow: 0 0 12px rgba(26, 92, 53, 0.4);
}

.btn-secondary {
  background: var(--bg-card);
  color: var(--text-body);
  border-color: var(--border);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-heading);
}

.btn-danger {
  background: rgba(224, 85, 85, 0.15);
  color: #f08080;
  border-color: var(--danger);
}

.btn-danger:hover {
  background: rgba(224, 85, 85, 0.3);
}

.btn-sm {
  padding: 5px 10px;
  font-size: 0.65rem;
}

/* ============================================================
   Tables
   ============================================================ */

.table-wrap {
  overflow-x: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.72rem;
}

thead th {
  background: rgba(26, 92, 53, 0.15);
  color: var(--text-label);
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  text-align: left;
}

tbody tr {
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  transition: background 0.15s;
}

tbody tr:hover {
  background: rgba(255, 255, 255, 0.03);
}

tbody td {
  padding: 9px 14px;
  color: var(--text-body);
  vertical-align: middle;
}

/* ============================================================
   Forms
   ============================================================ */

.form-group {
  margin-bottom: 14px;
}

label {
  display: block;
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--text-label);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 5px;
}

input[type=text],
input[type=email],
input[type=password],
input[type=url],
input[type=number],
select,
textarea {
  width: 100%;
  padding: 9px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-heading);
  font-size: 0.75rem;
  font-family: inherit;
  outline: none;
  transition: var(--transition);
}

input:focus, select:focus, textarea:focus {
  border-color: var(--green-primary);
  box-shadow: 0 0 0 3px rgba(26, 92, 53, 0.2);
  background: rgba(255, 255, 255, 0.07);
}

textarea { resize: vertical; min-height: 80px; }

select option { background: #0c1a10; color: var(--text-body); }

/* ============================================================
   Pipeline / Kanban
   ============================================================ */

.pipeline {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 12px;
  align-items: flex-start;
}

.pipeline-col {
  flex-shrink: 0;
  width: 200px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 12px;
}

.pipeline-col-header {
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--text-label);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

.pipeline-item {
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  margin-bottom: 6px;
  font-size: 0.7rem;
  color: var(--text-body);
  transition: var(--transition);
}

.pipeline-item:hover {
  border-color: var(--green-primary);
  background: rgba(26, 92, 53, 0.1);
}

/* ============================================================
   Details / Summary (task forms)
   ============================================================ */

details summary {
  cursor: pointer;
  font-size: 0.68rem;
  color: var(--text-muted);
  font-weight: 600;
  padding: 4px 0;
  list-style: none;
  user-select: none;
  transition: var(--transition);
}

details summary:hover { color: var(--text-body); }
details[open] summary { color: var(--green-glow); }

.task-form {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.task-form textarea {
  min-height: 60px;
  font-size: 0.7rem;
}

/* ============================================================
   Meta / utility
   ============================================================ */

.meta {
  font-size: 0.65rem;
  color: var(--text-muted);
}

.mb-4 { margin-bottom: 4px; }

.text-danger { color: var(--danger); }
.text-success { color: var(--green-glow); }
.text-muted { color: var(--text-muted); }

/* ============================================================
   Dashboard Particles (index.html only)
   ============================================================ */

.particle-field {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 0;
}

.particle {
  position: absolute;
  width: 2px;
  height: 2px;
  background: var(--green-glow);
  border-radius: 50%;
  opacity: 0;
  animation: float-up linear infinite;
}

.particle:nth-child(1)  { left: 8%;  animation-duration: 6s;   animation-delay: 0s;   }
.particle:nth-child(2)  { left: 18%; animation-duration: 8s;   animation-delay: 1s;   width: 3px; height: 3px; }
.particle:nth-child(3)  { left: 30%; animation-duration: 5.5s; animation-delay: 2s;   }
.particle:nth-child(4)  { left: 42%; animation-duration: 7s;   animation-delay: 0.5s; }
.particle:nth-child(5)  { left: 55%; animation-duration: 6.5s; animation-delay: 1.5s; width: 3px; height: 3px; }
.particle:nth-child(6)  { left: 68%; animation-duration: 5s;   animation-delay: 3s;   }
.particle:nth-child(7)  { left: 78%; animation-duration: 7.5s; animation-delay: 0.8s; }
.particle:nth-child(8)  { left: 88%; animation-duration: 6s;   animation-delay: 2.5s; width: 3px; height: 3px; }

/* ============================================================
   Animations
   ============================================================ */

@keyframes float-up {
  0%   { opacity: 0;   transform: translateY(100vh) scale(1); }
  10%  { opacity: 0.5; }
  90%  { opacity: 0.2; }
  100% { opacity: 0;   transform: translateY(-40px) scale(0.5); }
}

@keyframes shimmer {
  0%, 100% { opacity: 0; }
  50%       { opacity: 1; }
}

@keyframes glow-scan {
  0%   { width: 0;   opacity: 0; }
  50%  { width: 60px; opacity: 1; }
  100% { width: 0;   opacity: 0; left: 100%; }
}

@keyframes pulse-glow {
  0%, 100% { box-shadow: 0 0 6px rgba(26, 92, 53, 0.3); }
  50%       { box-shadow: 0 0 16px rgba(46, 204, 113, 0.6); }
}

@keyframes count-in {
  0%   { opacity: 0; transform: translateY(8px); }
  100% { opacity: 1; transform: translateY(0); }
}

/* ============================================================
   Mobile responsive
   ============================================================ */

@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.25s ease;
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .sidebar-overlay.open {
    display: block;
  }

  .main-content {
    margin-left: 0;
  }

  .hamburger {
    display: block;
  }

  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .agent-grid {
    grid-template-columns: 1fr;
  }

  .pipeline {
    flex-direction: column;
  }

  .pipeline-col {
    width: 100%;
  }

  .page-body {
    padding: 16px;
  }

  .topbar {
    padding: 12px 16px;
  }
}
```

- [ ] **Step 3: Verify the file was written**

```bash
wc -l "Owner Inbox/static/style.css"
```
Expected: 400+ lines

- [ ] **Step 4: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/static/style.css"
git commit -m "feat: replace style.css with Dark Forest design system"
```

---

## Task 2: Restructure `base.html` — sidebar layout

**Files:**
- Replace: `Owner Inbox/templates/base.html`

The current base uses a horizontal top `<nav>` + `<div class="container">`. The new design wraps everything in `.app-shell` with a fixed `.sidebar` and `.main-content`. The chat widget and its script/style are preserved unchanged.

- [ ] **Step 1: Write the new `base.html`**

Replace the entire file. Keep the chat widget block exactly as-is (lines 54–165 of the original):

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RO Marketing Tools</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>

<div class="app-shell">

  <!-- Sidebar -->
  <nav class="sidebar" id="sidebar">
    <a href="{{ url_for('index') }}" class="sidebar-logo">
      <div class="sidebar-logo-mark">RO</div>
      <div class="sidebar-logo-text">
        Owner Inbox
        <small>Roberts Oxygen</small>
      </div>
    </a>

    <div class="sidebar-nav">
      <a href="{{ url_for('index') }}" class="{{ 'active' if request.endpoint == 'index' else '' }}">Dashboard</a>

      <div class="sidebar-section-label">CRM</div>
      <a href="{{ url_for('contacts_list') }}" class="{{ 'active' if request.endpoint in ['contacts_list','contacts_new','contacts_view','contacts_edit'] else '' }}">Contacts</a>
      <a href="{{ url_for('leads_list') }}" class="{{ 'active' if request.endpoint in ['leads_list','leads_new','leads_edit'] else '' }}">Leads</a>
      <a href="{{ url_for('deals_list') }}" class="{{ 'active' if request.endpoint in ['deals_list','deals_new','deals_edit'] else '' }}">Deals</a>
      <a href="{{ url_for('pipeline') }}" class="{{ 'active' if request.endpoint == 'pipeline' else '' }}">Pipeline</a>

      <div class="sidebar-section-label">RO Leads</div>
      <a href="{{ url_for('ro_profiles') }}" class="{{ 'active' if request.endpoint in ['ro_profiles','ro_profile_view','ro_profile_add','ro_profile_edit'] else '' }}">Profiles</a>
      <a href="{{ url_for('ro_contacts') }}" class="{{ 'active' if request.endpoint in ['ro_contacts','ro_contact_add','ro_contact_edit'] else '' }}">Contacts</a>
      <a href="{{ url_for('ro_pipeline') }}" class="{{ 'active' if request.endpoint == 'ro_pipeline' else '' }}">Pipeline</a>
      <a href="{{ url_for('ro_search') }}" class="{{ 'active' if request.endpoint == 'ro_search' else '' }}">Search</a>
      <a href="{{ url_for('ro_info') }}" class="{{ 'active' if request.endpoint == 'ro_info' else '' }}">RO Info</a>

      <div class="sidebar-section-label">Work</div>
      <a href="{{ url_for('projects_list') }}" class="{{ 'active' if request.endpoint in ['projects_list','projects_view','projects_new','projects_edit','tasks_new','tasks_edit'] else '' }}">Projects</a>
      <a href="{{ url_for('files_list') }}" class="{{ 'active' if request.endpoint in ['files_list','files_new','files_view','files_edit'] else '' }}">Files</a>
      <a href="{{ url_for('kb_list') }}" class="{{ 'active' if request.endpoint in ['kb_list','kb_new','kb_view','kb_edit'] else '' }}">Knowledge Base</a>
      <a href="{{ url_for('competitors') }}" class="{{ 'active' if request.endpoint == 'competitors' else '' }}">Competitors</a>

      <div class="sidebar-section-label">Tools</div>
      <a href="https://comfyui23.siliconsoul.cloud" target="_blank">Image Creator ↗</a>
    </div>
  </nav>

  <!-- Mobile overlay -->
  <div class="sidebar-overlay" id="sidebarOverlay" onclick="closeSidebar()"></div>

  <!-- Main content -->
  <main class="main-content">
    <div class="topbar">
      <button class="hamburger" onclick="openSidebar()" aria-label="Open menu">&#9776;</button>
      <h1 class="page-title">{% block page_title %}Owner Inbox{% endblock %}</h1>
    </div>

    <div class="page-body">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, message in messages %}
          <div class="flash flash-{{ category }}">{{ message }}</div>
        {% endfor %}
      {% endwith %}

      {% block content %}{% endblock %}
    </div>
  </main>

</div>

<!-- Floating AI Chat -->
<button id="chatToggleBtn" onclick="toggleChat()" title="AI Assistant" style="
    position:fixed; bottom:24px; right:24px; z-index:1000;
    width:52px; height:52px; border-radius:50%; border:none; cursor:pointer;
    background:#1a5c35; color:#fff; font-size:1.4rem; box-shadow:0 4px 16px rgba(0,0,0,0.4);
    display:flex; align-items:center; justify-content:center;">&#128172;</button>

<div id="chatWidget" style="display:none; position:fixed; bottom:88px; right:24px; z-index:999;
    width:360px; height:480px; background:#0c1a10; border:1px solid #1a3a20; border-radius:12px;
    box-shadow:0 8px 32px rgba(0,0,0,0.5); display:none; flex-direction:column; overflow:hidden;">

    <div style="padding:12px 16px; background:#070f09; border-bottom:1px solid #1a3a20; display:flex; justify-content:space-between; align-items:center;">
        <span style="font-weight:600; font-size:0.9rem; color:#f0fff4;">AI Assistant</span>
        <div style="display:flex; align-items:center; gap:8px;">
            <div class="model-toggle" id="chatModelToggle">
                <button class="model-btn active" data-model="claude" onclick="setChatModel('claude',this)">Claude</button>
                <button class="model-btn" data-model="minimax" onclick="setChatModel('minimax',this)">MiniMax</button>
            </div>
            <button onclick="toggleChat()" style="background:none;border:none;color:#5a8a6a;cursor:pointer;font-size:1.1rem;">✕</button>
        </div>
    </div>

    <div id="chatMessages" style="flex:1; overflow-y:auto; padding:12px; display:flex; flex-direction:column; gap:10px;"></div>

    <div style="padding:10px; border-top:1px solid #1a3a20; display:flex; gap:8px;">
        <input id="chatInput" type="text" placeholder="Ask anything…" style="
            flex:1; padding:8px 12px; border-radius:8px; border:1px solid #1a3a20;
            background:#070f09; color:#f0fff4; font-size:0.85rem; outline:none;"
            onkeydown="if(event.key==='Enter')sendChat()">
        <button onclick="sendChat()" style="
            padding:8px 14px; border-radius:8px; border:none; cursor:pointer;
            background:#1a5c35; color:#fff; font-size:0.82rem; font-weight:600;">Send</button>
    </div>
</div>

<style>
.model-toggle { display:flex; background:#070f09; border-radius:6px; padding:2px; gap:2px; }
.model-btn {
    padding:3px 10px; border:none; border-radius:4px; cursor:pointer;
    font-size:0.72rem; font-weight:600; background:transparent; color:#5a8a6a; transition:all .15s;
}
.model-btn.active { background:#1a5c35; color:#fff; }
</style>

<script>
let _chatModel = localStorage.getItem('preferredModel') || 'claude';
let _chatHistory = [];

function openSidebar() {
    document.getElementById('sidebar').classList.add('open');
    document.getElementById('sidebarOverlay').classList.add('open');
}

function closeSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('sidebarOverlay').classList.remove('open');
}

function toggleChat() {
    const w = document.getElementById('chatWidget');
    w.style.display = w.style.display === 'flex' ? 'none' : 'flex';
    if (w.style.display === 'flex') {
        const saved = localStorage.getItem('preferredModel') || 'claude';
        setChatModel(saved, document.querySelector(`#chatModelToggle [data-model="${saved}"]`));
        document.getElementById('chatInput').focus();
    }
}

function setChatModel(model, btn) {
    _chatModel = model;
    localStorage.setItem('preferredModel', model);
    if (!btn) return;
    document.querySelectorAll('#chatModelToggle .model-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

function appendMsg(role, text) {
    const box = document.getElementById('chatMessages');
    const div = document.createElement('div');
    div.style.cssText = `display:flex; justify-content:${role==='user'?'flex-end':'flex-start'};`;
    const bubble = document.createElement('div');
    bubble.style.cssText = `max-width:85%; padding:8px 12px; border-radius:10px; font-size:0.82rem; line-height:1.5; white-space:pre-wrap; word-break:break-word; background:${role==='user'?'#1a5c35':'rgba(255,255,255,0.06)'}; color:${role==='user'?'#fff':'#c8e6ce'};`;
    bubble.textContent = text;
    div.appendChild(bubble);
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
}

async function sendChat() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text) return;
    input.value = '';
    appendMsg('user', text);
    _chatHistory.push({role:'user', content: text});

    const thinking = document.createElement('div');
    thinking.id = 'chatThinking';
    thinking.style.cssText = 'color:#5a8a6a; font-size:0.78rem; padding:4px 8px;';
    thinking.textContent = _chatModel === 'minimax' ? 'MiniMax thinking…' : 'Claude thinking…';
    document.getElementById('chatMessages').appendChild(thinking);

    try {
        const res = await fetch('/chat', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({messages: _chatHistory, model: _chatModel})
        });
        const data = await res.json();
        document.getElementById('chatThinking')?.remove();
        if (data.error) {
            appendMsg('assistant', '⚠ ' + data.error);
        } else {
            appendMsg('assistant', data.response);
            _chatHistory.push({role:'assistant', content: data.response});
        }
    } catch(e) {
        document.getElementById('chatThinking')?.remove();
        appendMsg('assistant', '⚠ Request failed.');
    }
}
</script>

</body>
</html>
```

- [ ] **Step 2: Verify `request.endpoint` works in Jinja2**

Flask's `request` object is available in templates by default. The active-link logic `{{ 'active' if request.endpoint == 'index' else '' }}` requires no changes to `app.py`.

- [ ] **Step 3: Start the app and verify the sidebar renders**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools/Owner Inbox"
python3 app.py
```

Open `http://localhost:5000` in browser (PIN: 6911). Confirm:
- Sidebar appears on left, 200px wide, dark green background
- Dashboard link is active (highlighted)
- Main content fills remaining width
- Chat button is visible bottom-right

- [ ] **Step 4: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/templates/base.html"
git commit -m "feat: replace top-nav with Dark Forest sidebar layout"
```

---

## Task 3: Update `index.html` — particles + count-in

**Files:**
- Modify: `Owner Inbox/templates/index.html`

Add a particle field div before the stat grid, and add a `page_title` block so the topbar shows the right title.

- [ ] **Step 1: Write the updated `index.html`**

Replace the entire file with:

```html
{% extends 'base.html' %}
{% block page_title %}Dashboard{% endblock %}
{% block content %}

<!-- Floating particles (CSS-animated, behind content) -->
<div class="particle-field" aria-hidden="true">
  <div class="particle"></div>
  <div class="particle"></div>
  <div class="particle"></div>
  <div class="particle"></div>
  <div class="particle"></div>
  <div class="particle"></div>
  <div class="particle"></div>
  <div class="particle"></div>
</div>

<div class="stat-grid" style="position:relative;z-index:1;">
    <div class="stat-card">
        <div class="count">{{ counts.files }}</div>
        <div class="label">Files in Catalog</div>
    </div>
    <div class="stat-card">
        <div class="count">{{ counts.articles }}</div>
        <div class="label">KB Articles</div>
    </div>
    <div class="stat-card">
        <div class="count">{{ counts.contacts }}</div>
        <div class="label">CRM Contacts</div>
    </div>
    <div class="stat-card">
        <div class="count">{{ counts.deals }}</div>
        <div class="label">Deals</div>
    </div>
    <div class="stat-card">
        <div class="count">{{ counts.active_projects }}</div>
        <div class="label">Active Projects</div>
    </div>
    <div class="stat-card">
        <div class="count">{{ counts.open_tasks }}</div>
        <div class="label">Open Tasks</div>
    </div>
    <div class="stat-card">
        <div class="count">{{ counts.working_agents }}</div>
        <div class="label">Active Agents</div>
    </div>
    <div class="stat-card">
        <div class="count">{{ counts.ro_prospects }}</div>
        <div class="label">Total Prospects</div>
    </div>
    <div class="stat-card">
        <div class="count">{{ counts.ro_new_prospects }}</div>
        <div class="label">New Prospects</div>
    </div>
</div>

<h2 class="section-title" style="position:relative;z-index:1;">Team</h2>
<div class="agent-grid" style="position:relative;z-index:1;">
{% for agent in agents %}
<div class="agent-card">
    <div>
        <span class="badge badge-{{ agent['status'] }}">{{ agent['status'] }}</span>
    </div>
    <h2>{{ agent['name'] }}</h2>
    <div class="agent-role">{{ agent['role'] }}</div>

    {% if agent['current_task'] %}
    <div>
        <div class="meta mb-4">Current Task:</div>
        <div class="current-task">{{ agent['current_task'] }}</div>
    </div>
    {% endif %}

    <div class="meta">
        <strong>Skills:</strong> {{ agent['skills'] or '—' }}
    </div>
    <div class="meta">
        <strong>Model:</strong> {{ agent['model'] or '—' }}
    </div>
    <details>
        <summary>Send Task &#9660;</summary>
        <form class="task-form" method="post" action="{{ url_for('agent_task', id=agent['id']) }}">
            <textarea name="task" rows="3" placeholder="Describe task..."></textarea>
            <button type="submit">Assign Task</button>
        </form>
    </details>
</div>
{% endfor %}
</div>

{% endblock %}
```

- [ ] **Step 2: Verify in browser**

Open `http://localhost:5000`. Confirm:
- Particles float up slowly in the background behind the stat grid
- Stat numbers animate in (count-in) on each page load/refresh
- Particle field doesn't block clicking on cards

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/templates/index.html"
git commit -m "feat: add particles and count-in animation to dashboard"
```

---

## Task 4: Update `lock.html`

**Files:**
- Modify: `Owner Inbox/templates/lock.html`

Restyle the inline `<style>` block to match Dark Forest tokens.

- [ ] **Step 1: Write the updated `lock.html`**

Replace the entire file with:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Owner Inbox — Locked</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
  <style>
    body {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: #0c1a10;
    }
    .lock-box {
      background: rgba(255,255,255,0.04);
      border: 1px solid #1a3a20;
      border-radius: 14px;
      padding: 48px 40px;
      text-align: center;
      width: 320px;
      position: relative;
      overflow: hidden;
    }
    /* Shimmer top edge */
    .lock-box::before {
      content: '';
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 1px;
      background: linear-gradient(90deg, transparent, #2ecc71, transparent);
      animation: shimmer 3s ease-in-out infinite;
    }
    @keyframes shimmer { 0%,100%{opacity:0} 50%{opacity:1} }
    .lock-icon { font-size: 40px; margin-bottom: 14px; }
    .lock-box h1 {
      font-size: 1.1rem;
      font-weight: 800;
      margin-bottom: 6px;
      color: #f0fff4;
    }
    .lock-box p { color: #5a8a6a; margin-bottom: 24px; font-size: 0.78rem; }
    .lock-box input[type=password] {
      width: 100%;
      padding: 12px 16px;
      font-size: 1.4rem;
      letter-spacing: 10px;
      text-align: center;
      background: rgba(255,255,255,0.05);
      border: 1px solid #1a3a20;
      border-radius: 8px;
      color: #f0fff4;
      margin-bottom: 14px;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .lock-box input[type=password]:focus {
      border-color: #1a5c35;
      box-shadow: 0 0 0 3px rgba(26,92,53,0.2);
    }
    .lock-box button {
      width: 100%;
      padding: 11px;
      background: #1a5c35;
      color: #f0fff4;
      border: none;
      border-radius: 8px;
      font-size: 0.82rem;
      font-weight: 700;
      cursor: pointer;
      letter-spacing: 0.05em;
      transition: background 0.2s, box-shadow 0.2s;
    }
    .lock-box button:hover {
      background: #225f3a;
      box-shadow: 0 0 16px rgba(26,92,53,0.5);
    }
    .error { color: #f08080; font-size: 0.78rem; margin-bottom: 12px; }
  </style>
</head>
<body>
  <div class="lock-box">
    <div class="lock-icon">🔒</div>
    <h1>Owner Inbox</h1>
    <p>Enter your PIN to continue</p>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST" action="/unlock">
      <input type="password" name="pin" placeholder="••••" maxlength="10" autofocus>
      <button type="submit">Unlock</button>
    </form>
  </div>
</body>
</html>
```

- [ ] **Step 2: Verify in browser**

Open `http://localhost:5000/lock` (or log out). Confirm:
- Dark green background, lock box visible centered
- Shimmer animation on top of the card
- PIN input has dark styling
- Unlock button is hunter green

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/templates/lock.html"
git commit -m "feat: restyle lock page with Dark Forest theme"
```

---

## Task 5: Add `page_title` blocks to all remaining templates

**Files:**
- Modify: All templates in `crm/`, `projects/`, `ro/`, `knowledge_base/`, `file_catalog/`, plus `competitors.html`, `team.html`

These templates already render correctly with the new CSS via `base.html`. The only change needed is adding `{% block page_title %}...{% endblock %}` so the topbar shows the right page name instead of the default "Owner Inbox".

- [ ] **Step 1: Add page_title blocks**

For each template listed below, add this block immediately after `{% extends 'base.html' %}` and before `{% block content %}`. The title text to use is shown for each file:

| Template | Title text |
|---|---|
| `crm/contacts_list.html` | Contacts |
| `crm/contact_form.html` | Add Contact |
| `crm/contact_view.html` | Contact |
| `crm/leads_list.html` | Leads |
| `crm/lead_form.html` | Add Lead |
| `crm/deals_list.html` | Deals |
| `crm/deal_form.html` | Add Deal |
| Note: `team.html` has no route in app.py — skip it |
| `crm/pipeline.html` | CRM Pipeline |
| `projects/list.html` | Projects |
| `projects/form.html` | New Project |
| `projects/view.html` | Project |
| `projects/task_form.html` | Add Task |
| `ro/profiles.html` | RO Profiles |
| `ro/profile_view.html` | Prospect Profile |
| `ro/profile_add.html` | Add Prospect |
| `ro/contacts.html` | RO Contacts |
| `ro/contact_add.html` | Add Contact |
| `ro/contact_edit.html` | Edit Contact |
| `ro/pipeline.html` | RO Pipeline |
| `ro/search.html` | Search Prospects |
| `ro/info.html` | Roberts Oxygen Info |
| `knowledge_base/list.html` | Knowledge Base |
| `knowledge_base/form.html` | New Article |
| `knowledge_base/view.html` | Article |
| `file_catalog/list.html` | File Catalog |
| `file_catalog/form.html` | Add File |
| `file_catalog/view.html` | File |
| `competitors.html` | Competitors |
| `team.html` | AI Team |

For each file, open it and insert after the first line (`{% extends 'base.html' %}`):

```jinja
{% block page_title %}[Title from table above]{% endblock %}
```

Example — `crm/contacts_list.html` first 3 lines become:
```jinja
{% extends 'base.html' %}
{% block page_title %}Contacts{% endblock %}
{% block content %}
```

- [ ] **Step 2: Spot-check 3 pages in browser**

Navigate to `/crm/contacts`, `/projects`, `/ro/profiles`. Confirm each shows its correct title in the topbar.

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/templates/"
git commit -m "feat: add page_title blocks to all templates"
```

---

## Task 6: Full visual smoke test

**Files:** None modified — read-only verification

- [ ] **Step 1: Verify the app is running**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/lock
```
Expected: `200`

- [ ] **Step 2: Check all major routes load without 500 errors**

Log in at `http://localhost:5000` (PIN: 6911), then manually open each of these URLs and confirm no 500 errors:

```
/                     → Dashboard
/crm/contacts         → Contacts list
/crm/leads            → Leads list
/crm/deals            → Deals list
/crm/pipeline         → Pipeline kanban
/projects             → Projects list
/ro/profiles          → RO Profiles
/ro/contacts          → RO Contacts
/ro/pipeline          → RO Pipeline
/files                → File catalog
/kb                   → Knowledge base
/competitors          → Competitors
```

- [ ] **Step 3: Check mobile view**

In browser DevTools, set viewport to 375px width. Confirm:
- Sidebar is hidden (no sidebar visible on left)
- Hamburger `☰` button appears in topbar
- Clicking hamburger opens sidebar overlay
- Clicking overlay closes sidebar

- [ ] **Step 4: Final commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add -A
git commit -m "feat: complete Dark Forest UI redesign — all templates updated"
```
