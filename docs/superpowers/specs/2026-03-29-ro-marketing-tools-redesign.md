# RO Marketing Tools — UI Redesign Spec
**Date:** 2026-03-29
**Status:** Approved
**Scope:** Full app UI redesign — all 31 Jinja2 templates + style.css replacement

---

## Design Direction: Dark Forest Refined

Hunter green dominant, dark background, floating particle ambiance, glowing accents. Lighter body text and larger typography than the original.

---

## Color Tokens

| Token | Value | Usage |
|---|---|---|
| `--bg-page` | `#0c1a10` | Main canvas background |
| `--bg-chrome` | `#070f09` | Sidebar, nav headers |
| `--green-primary` | `#1a5c35` | Active nav, primary buttons, cards |
| `--green-glow` | `#2ecc71` | Animations, badges, accent dots |
| `--bg-card` | `rgba(255,255,255,0.05)` | Stat cards, table rows |
| `--border` | `#1a3a20` | All borders and dividers |
| `--text-heading` | `#f0fff4` | H1, H2, stat numbers |
| `--text-body` | `#c8e6ce` | List rows, descriptions |
| `--text-label` | `#6db87e` | Uppercase labels, sublabels |
| `--text-muted` | `#5a8a6a` | Nav items, inactive states |

---

## Typography Scale

| Role | Size | Weight | Notes |
|---|---|---|---|
| Page title | 1.1rem | 800 | Letter-spacing -0.01em |
| Section heading | 0.85rem | 700 | |
| Stat number | 1.4rem | 800 | Color: `--text-heading` |
| Body / list row | 0.72rem | 400 | Color: `--text-body` |
| Card label | 0.62rem | 700 | Uppercase, letter-spacing 0.1em |
| Nav item | 0.65rem | 600 | Uppercase, letter-spacing 0.05em |

Font: `'Segoe UI', system-ui, sans-serif` (no external fonts)

---

## Layout Structure

- **Sidebar nav** — 88px wide, `--bg-chrome`, icon+label nav items, active state with `--green-primary` bg + glow shadow
- **Main content area** — fills remaining width, `--bg-page` background
- **Top bar** — page title (left) + status badge (right) on each page
- **Mobile** — sidebar collapses to hamburger menu (existing behavior preserved)

---

## Animation Inventory

| Animation | Where used | Behavior |
|---|---|---|
| **Glow scan bar** | Section dividers, card tops | Green light sweeps left→right, 2.5s loop |
| **Card shimmer** | Stat cards (top edge) | Gradient shimmer, staggered 1s delay per card |
| **Pulse badge** | LIVE/status badges | Box-shadow breathes, 2s ease-in-out loop |
| **Floating particles** | Dashboard background | 6–8 particles float up from bottom, opacity fade |
| **Count-in numbers** | Stat numbers on page load | Fade + translateY(8px→0), 0.4s ease-out, once |

All animations are CSS-only. No JS animation libraries.

---

## Pages in Scope

All 31 templates updated. Key pages:

- `base.html` — layout shell, sidebar nav, hamburger mobile menu
- `index.html` — dashboard with stat cards, agent status, recent activity
- `lock.html` — PIN login page
- `crm/` — contacts, leads, deals, pipeline kanban
- `projects/` — project list, project detail, task views
- `ro/` — prospect profiles, prospect pipeline, contact list
- `kb/` — knowledge base article list and detail
- `file_catalog/` — file list and detail

`static/style.css` is fully replaced with the new design system.

---

## What Is NOT Changing

- No changes to `app.py`, `database.py`, `monitor.py`, or any Python files
- No changes to routes or functionality
- No new dependencies
- Existing Jinja2 template structure and block names preserved
- Mobile responsiveness preserved (flexbox + media queries)
