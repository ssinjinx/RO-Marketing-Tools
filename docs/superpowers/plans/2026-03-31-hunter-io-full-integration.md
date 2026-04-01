# Hunter.io Full Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand Hunter.io from a single domain-search helper into a full prospecting and contact-verification pipeline with four new API helpers, parallel search merging, email verification badges, a usage widget, and a working batch script.

**Architecture:** All new Hunter helper functions live in `app.py` next to the existing `find_with_hunter()`. DB columns are added via a migration in `get_db()`. The search job runs Apify and Hunter Discover in parallel threads and merges results before returning. UI badges are rendered server-side in Jinja templates.

**Tech Stack:** Python 3, Flask, SQLite, `requests` (already imported as `http_requests`), Jinja2, vanilla JS (fetch API)

---

## File Map

| File | Change |
|------|--------|
| `Owner Inbox/app.py` | Add 4 helpers near line 1465; modify `get_db` migration; modify `_run_search_job` (line 936); modify `ro_find_contacts` (line 1608); add `/ro/hunter/usage` route |
| `Owner Inbox/database.py` | Add migration for `verified`/`verification_status` columns in `get_db()` |
| `Owner Inbox/hunter_batch_finder.py` | Complete rewrite |
| `Owner Inbox/templates/ro/profile_view.html` | Add verification badge in email cell (line 141) |
| `Owner Inbox/templates/ro/search.html` | Add usage widget after form (line 69); add Hunter badges in result cards |

---

## Task 1: DB migration for verification columns

**Files:**
- Modify: `Owner Inbox/database.py`

- [ ] **Step 1: Add migration to `get_db()`**

Open `Owner Inbox/database.py`. Replace the current `get_db()` function:

```python
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        # Migrations: add columns if missing
        existing = {row[1] for row in g.db.execute("PRAGMA table_info(ro_contacts)").fetchall()}
        if 'verified' not in existing:
            g.db.execute("ALTER TABLE ro_contacts ADD COLUMN verified INTEGER DEFAULT 0")
            g.db.commit()
        if 'verification_status' not in existing:
            g.db.execute("ALTER TABLE ro_contacts ADD COLUMN verification_status TEXT DEFAULT 'unverified'")
            g.db.commit()
    return g.db
```

- [ ] **Step 2: Verify migration runs**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools/Owner Inbox"
python3 -c "
from app import app
with app.app_context():
    from database import get_db
    db = get_db()
    cols = {row[1] for row in db.execute('PRAGMA table_info(ro_contacts)').fetchall()}
    assert 'verified' in cols, 'verified column missing'
    assert 'verification_status' in cols, 'verification_status column missing'
    print('OK - both columns present')
"
```
Expected: `OK - both columns present`

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/database.py"
git commit -m "feat: add verified/verification_status columns to ro_contacts via migration"
```

---

## Task 2: Four Hunter helper functions

**Files:**
- Modify: `Owner Inbox/app.py` (insert after line 1464, after `find_with_hunter`)

- [ ] **Step 1: Add the four helpers**

In `app.py`, directly after the closing `except` of `find_with_hunter()` (after line 1464), insert:

```python

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
```

- [ ] **Step 2: Verify functions load without error**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools/Owner Inbox"
python3 -c "
from app import app
with app.app_context():
    from app import hunter_verify_email, hunter_find_email, hunter_discover, hunter_account_info
    print('All 4 helpers imported OK')
    info = hunter_account_info()
    print(f'Account info: {info}')
"
```
Expected: `All 4 helpers imported OK` followed by dict with search/verification counts.

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/app.py"
git commit -m "feat: add hunter_verify_email, hunter_find_email, hunter_discover, hunter_account_info helpers"
```

---

## Task 3: `/ro/hunter/usage` route

**Files:**
- Modify: `Owner Inbox/app.py` (add route near other `/ro/` routes)

- [ ] **Step 1: Add the route**

Find the line `@app.route('/ro/profiles/<int:prospect_id>/find-contacts'` (around line 1608) and insert this new route directly before it:

```python
@app.route('/ro/hunter/usage')
def ro_hunter_usage():
    return jsonify(hunter_account_info())


```

- [ ] **Step 2: Test the route**

Start the app if not running:
```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools/Owner Inbox" && python3 app.py &
sleep 2
curl -s http://localhost:5000/ro/hunter/usage | python3 -m json.tool
```
Expected: JSON with `searches_used`, `searches_left`, `verifications_used`, `verifications_left`.

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/app.py"
git commit -m "feat: add /ro/hunter/usage route"
```

---

## Task 4: Modify `ro_find_contacts` — Email Finder fallback + verification

**Files:**
- Modify: `Owner Inbox/app.py` — `ro_find_contacts` function (around line 1611)

- [ ] **Step 1: Replace the `ro_find_contacts` function body**

Find the function starting at `@app.route('/ro/profiles/<int:prospect_id>/find-contacts'`. Replace the entire function body with:

```python
@app.route('/ro/profiles/<int:prospect_id>/find-contacts', methods=['POST'])
def ro_find_contacts(prospect_id):
    db = get_db()
    prospect = db.execute('SELECT * FROM prospects WHERE id = ?', (prospect_id,)).fetchone()
    if not prospect:
        return jsonify({'error': 'Prospect not found'}), 404
    if not prospect['website']:
        return jsonify({'error': 'No website on file for this prospect'}), 400

    from urllib.parse import urlparse

    # 1. Hunter.io domain search
    raw_contacts = find_with_hunter(prospect['website'])
    source = 'hunter'

    # 2. Hunter Email Finder fallback — if no named contacts from domain search
    if not any(c['name'] for c in raw_contacts):
        parsed = urlparse(prospect['website'])
        domain = (parsed.netloc or parsed.path).lstrip('www.')
        name_parts = (prospect['business_name'] or '').split()
        first = name_parts[0] if name_parts else ''
        last = name_parts[1] if len(name_parts) > 1 else ''
        found = hunter_find_email(first, last, domain)
        if found:
            raw_contacts = [{'email': found['email'], 'name': prospect['business_name'] or '', 'title': ''}]
            source = 'hunter_finder'

    # 3. Website scraper
    if not raw_contacts:
        emails = find_best_contacts(prospect['website'])
        raw_contacts = [{'email': e, 'name': '', 'title': ''} for e in emails]
        source = 'scrape'

    # 4. Email format guesser + SMTP verification
    if not raw_contacts:
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
        # Verify email via Hunter
        verification = hunter_verify_email(email)
        verified = verification['status'] in ('valid', 'accept_all')

        existing = db.execute('SELECT id FROM ro_contacts WHERE prospect_id=? AND email=?', (prospect_id, email)).fetchone()
        if not existing:
            db.execute(
                'INSERT INTO ro_contacts (prospect_id, name, title, email, is_suggested, verified, verification_status) VALUES (?, ?, ?, ?, 1, ?, ?)',
                (prospect_id, c['name'], c['title'], email, 1 if verified else 0, verification['status'])
            )
            db.commit()
        else:
            db.execute(
                'UPDATE ro_contacts SET verified=?, verification_status=? WHERE prospect_id=? AND email=?',
                (1 if verified else 0, verification['status'], prospect_id, email)
            )
            db.commit()
        contact = db.execute('SELECT * FROM ro_contacts WHERE prospect_id=? AND email=?', (prospect_id, email)).fetchone()
        saved.append({
            'id': contact['id'],
            'email': email,
            'name': contact['name'] or '',
            'title': contact['title'] or '',
            'verified': bool(contact['verified']),
            'verification_status': contact['verification_status'] or 'unverified',
        })

    return jsonify({'contacts': saved, 'source': source})
```

- [ ] **Step 2: Test the endpoint**

With the app running, navigate to any prospect profile with a website and click "Find Contacts". Check the browser console for the response — it should now include `verified` and `verification_status` per contact.

Or via curl (replace `1` with a real prospect ID that has a website):
```bash
curl -s -X POST http://localhost:5000/ro/profiles/1/find-contacts \
  -H "Content-Type: application/json" | python3 -m json.tool
```
Expected: contacts array with `"verified": true/false` and `"verification_status": "valid"/"accept_all"/"unknown"` etc.

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/app.py"
git commit -m "feat: add Hunter Email Finder fallback and email verification to find-contacts flow"
```

---

## Task 5: Modify `_run_search_job` — parallel Hunter Discover + merge

**Files:**
- Modify: `Owner Inbox/app.py` — `_run_search_job` function (line 936)

- [ ] **Step 1: Replace `_run_search_job`**

Find `def _run_search_job(job_id, business_type, area, zip_code=None, radius=None):` and replace the entire function:

```python
def _run_search_job(job_id, business_type, area, zip_code=None, radius=None):
    """Background thread: runs Apify + Hunter Discover in parallel and merges results."""
    token = os.environ.get('APIFY_TOKEN', '')
    if not token:
        _search_jobs[job_id] = {'status': 'error', 'error': 'APIFY_TOKEN not set'}
        return

    apify_results = []
    hunter_results = []
    apify_error = None

    def run_apify():
        nonlocal apify_results, apify_error
        try:
            client = ApifyClient(token)
            if zip_code:
                search_str = f"{business_type} near {zip_code} within {radius} miles" if radius else f"{business_type} near {zip_code}"
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
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                apify_results.append({
                    "title": item.get("title", ""),
                    "url": item.get("website", ""),
                    "display_url": item.get("website", ""),
                    "snippet": f"{item.get('address', '')} | {item.get('phoneUnformatted', '')} | Rating: {item.get('totalScore', 'N/A')}",
                    "address": item.get("address", ""),
                    "phone": item.get("phoneUnformatted", ""),
                    "rating": item.get("totalScore", ""),
                    "category": item.get("categoryName", ""),
                    "hunter_enriched": False,
                    "hunter_only": False,
                })
        except Exception as e:
            apify_error = str(e)

    def run_hunter():
        nonlocal hunter_results
        location = area or zip_code or ''
        hunter_results = hunter_discover(business_type, location, limit=10)

    t_apify = threading.Thread(target=run_apify, daemon=True)
    t_hunter = threading.Thread(target=run_hunter, daemon=True)
    t_apify.start()
    t_hunter.start()
    t_apify.join()
    t_hunter.join()

    if apify_error and not hunter_results:
        _search_jobs[job_id] = {'status': 'error', 'error': apify_error}
        return

    # Build Hunter lookup by domain
    from urllib.parse import urlparse

    def extract_domain(url):
        if not url:
            return ''
        if not url.startswith('http'):
            url = 'https://' + url
        return urlparse(url).netloc.lstrip('www.').lower()

    hunter_by_domain = {}
    for h in hunter_results:
        d = h.get('domain', '').lstrip('www.').lower()
        if d:
            hunter_by_domain[d] = h

    # Mark Apify results as hunter_enriched where domains match
    apify_domains_seen = set()
    for r in apify_results:
        d = extract_domain(r.get('url', ''))
        apify_domains_seen.add(d)
        if d and d in hunter_by_domain:
            r['hunter_enriched'] = True
            r['hunter_industry'] = hunter_by_domain[d].get('industry', '')
            r['hunter_size'] = hunter_by_domain[d].get('size', '')

    # Hunter-only results: not matched to any Apify result
    hunter_only = [
        h for h in hunter_results
        if h.get('domain', '').lstrip('www.').lower() not in apify_domains_seen
    ]
    for h in hunter_only:
        h['title'] = h.get('name', '')
        h['url'] = h.get('website', '')
        h['display_url'] = h.get('website', '')
        h['snippet'] = f"Industry: {h.get('industry', '—')} | Size: {h.get('size', '—')}"
        h['address'] = ''
        h['phone'] = ''
        h['rating'] = ''
        h['category'] = h.get('industry', '')
        h['hunter_only'] = True
        h['hunter_enriched'] = False

    # Order: hunter-enriched first, apify-only second, hunter-only last
    enriched = [r for r in apify_results if r.get('hunter_enriched')]
    apify_only = [r for r in apify_results if not r.get('hunter_enriched')]
    results = enriched + apify_only + hunter_only

    _search_jobs[job_id] = {
        'status': 'done',
        'results': results,
        'meta': {'business_type': business_type, 'area': area},
    }
```

- [ ] **Step 2: Verify app still starts**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools/Owner Inbox"
python3 -c "from app import app; print('app loaded OK')"
```
Expected: `app loaded OK`

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/app.py"
git commit -m "feat: run Hunter Discover in parallel with Apify, merge and order results"
```

---

## Task 6: Rewrite `hunter_batch_finder.py`

**Files:**
- Rewrite: `Owner Inbox/hunter_batch_finder.py`

- [ ] **Step 1: Rewrite the file**

```python
#!/usr/bin/env python3
"""
Hunter.io Batch Email Finder
Processes up to --limit prospects at a time from the DB.
Usage:
    python3 hunter_batch_finder.py           # process 10
    python3 hunter_batch_finder.py --limit 5
"""

import argparse
import os
import sqlite3
import time
from urllib.parse import urlparse

import requests

DB_PATH = 'instance/owner_inbox.db'
HUNTER_API = 'https://api.hunter.io/v2'


def get_api_key():
    key = os.environ.get('HUNTER_API_KEY', '')
    if not key:
        # Try loading from .env manually
        try:
            with open('.env') as f:
                for line in f:
                    if line.startswith('HUNTER_API_KEY='):
                        key = line.strip().split('=', 1)[1]
                        break
        except FileNotFoundError:
            pass
    return key


def account_info(api_key):
    try:
        r = requests.get(f'{HUNTER_API}/account', params={'api_key': api_key}, timeout=10)
        if r.status_code != 200:
            return None
        d = r.json().get('data', {})
        req = d.get('requests', {})
        searches = req.get('searches', {})
        verifications = req.get('verifications', {})
        return {
            'searches_used': searches.get('used', 0),
            'searches_left': searches.get('available', 0),
            'verifications_used': verifications.get('used', 0),
            'verifications_left': verifications.get('available', 0),
        }
    except Exception:
        return None


def domain_search(api_key, domain):
    """Returns list of {email, name, title} sorted named-first."""
    try:
        r = requests.get(
            f'{HUNTER_API}/domain-search',
            params={'domain': domain, 'api_key': api_key, 'limit': 5},
            timeout=10
        )
        if r.status_code != 200:
            return []
        contacts = []
        for e in r.json().get('data', {}).get('emails', []):
            if e.get('value'):
                contacts.append({
                    'email': e['value'].lower(),
                    'name': ' '.join(filter(None, [e.get('first_name', ''), e.get('last_name', '')])),
                    'title': e.get('position', ''),
                })
        named = [c for c in contacts if c['name']]
        generic = [c for c in contacts if not c['name']]
        return (named + generic)[:3]
    except Exception:
        return []


def find_email(api_key, first_name, last_name, domain):
    """Returns {email, confidence} or None."""
    if not first_name:
        return None
    try:
        r = requests.get(
            f'{HUNTER_API}/email-finder',
            params={'domain': domain, 'first_name': first_name, 'last_name': last_name or '', 'api_key': api_key},
            timeout=15
        )
        if r.status_code != 200:
            return None
        data = r.json().get('data', {})
        email = data.get('email')
        return {'email': email.lower(), 'confidence': data.get('score', 0)} if email else None
    except Exception:
        return None


def verify_email(api_key, email):
    """Returns {status, score}."""
    try:
        r = requests.get(
            f'{HUNTER_API}/email-verifier',
            params={'email': email, 'api_key': api_key},
            timeout=15
        )
        if r.status_code != 200:
            return {'status': 'unknown', 'score': 0}
        data = r.json().get('data', {})
        return {'status': data.get('status', 'unknown'), 'score': data.get('score', 0)}
    except Exception:
        return {'status': 'unknown', 'score': 0}


def get_prospects(conn, limit):
    cur = conn.cursor()
    cur.execute(
        "SELECT id, business_name, website FROM prospects WHERE status='new' AND website IS NOT NULL AND website != '' ORDER BY created_at ASC LIMIT ?",
        (limit,)
    )
    return cur.fetchall()


def save_contact(conn, prospect_id, email, name, title, verified, verification_status):
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM ro_contacts WHERE prospect_id=? AND email=?",
        (prospect_id, email)
    )
    if cur.fetchone():
        conn.execute(
            "UPDATE ro_contacts SET verified=?, verification_status=? WHERE prospect_id=? AND email=?",
            (1 if verified else 0, verification_status, prospect_id, email)
        )
    else:
        conn.execute(
            "INSERT INTO ro_contacts (prospect_id, name, title, email, is_suggested, verified, verification_status) VALUES (?,?,?,?,1,?,?)",
            (prospect_id, name, title, email, 1 if verified else 0, verification_status)
        )
    conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        print('ERROR: HUNTER_API_KEY not set in environment or .env file')
        return

    conn = sqlite3.connect(DB_PATH)

    # Check credits before starting
    before = account_info(api_key)
    if before:
        print(f"Credits before: {before['searches_left']} searches, {before['verifications_left']} verifications")
        if before['searches_left'] < 5:
            print('WARNING: Fewer than 5 searches remaining. Aborting to preserve credits.')
            conn.close()
            return
    else:
        print('WARNING: Could not fetch account info, proceeding anyway.')

    prospects = get_prospects(conn, args.limit)
    if not prospects:
        print('No unprocessed prospects with websites found.')
        conn.close()
        return

    print(f'\nProcessing {len(prospects)} prospects...\n')

    total_contacts = 0
    total_verified = 0

    for pid, name, website in prospects:
        print(f'  [{pid}] {name}')
        parsed = urlparse(website if website.startswith('http') else 'https://' + website)
        domain = parsed.netloc.lstrip('www.')

        contacts = domain_search(api_key, domain)
        source = 'domain_search'

        if not any(c['name'] for c in contacts):
            parts = name.split()
            found = find_email(api_key, parts[0] if parts else '', parts[1] if len(parts) > 1 else '', domain)
            if found:
                contacts = [{'email': found['email'], 'name': name, 'title': ''}]
                source = 'email_finder'

        if not contacts:
            print(f'    → No contacts found')
            conn.execute("UPDATE prospects SET status='profiled' WHERE id=?", (pid,))
            conn.commit()
            continue

        for c in contacts:
            v = verify_email(api_key, c['email'])
            verified = v['status'] in ('valid', 'accept_all')
            save_contact(conn, pid, c['email'], c['name'], c['title'], verified, v['status'])
            total_contacts += 1
            if verified:
                total_verified += 1
            status_icon = '✓' if verified else '~'
            print(f'    {status_icon} {c["email"]} [{v["status"]}] via {source}')
            time.sleep(0.3)  # gentle rate limiting

        conn.execute("UPDATE prospects SET status='profiled' WHERE id=?", (pid,))
        conn.commit()

    conn.close()

    after = account_info(api_key)
    print(f'\n─── Summary ───')
    print(f'Prospects processed : {len(prospects)}')
    print(f'Contacts found      : {total_contacts}')
    print(f'Contacts verified   : {total_verified}')
    if before and after:
        print(f'Searches used       : {before["searches_left"] - after["searches_left"]}')
        print(f'Verifications used  : {before["verifications_left"] - after["verifications_left"]}')
        print(f'Credits remaining   : {after["searches_left"]} searches, {after["verifications_left"]} verifications')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Test with dry run (check it imports and parses args)**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools/Owner Inbox"
python3 hunter_batch_finder.py --help
```
Expected: shows `--limit` option.

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/hunter_batch_finder.py"
git commit -m "feat: rewrite hunter_batch_finder.py with real API calls, verification, and credit tracking"
```

---

## Task 7: UI — verification badges in profile_view.html

**Files:**
- Modify: `Owner Inbox/templates/ro/profile_view.html`

- [ ] **Step 1: Add verification badge to email cell**

Find this line in `profile_view.html` (around line 141):
```html
            <td>{% if c.email %}<a href="mailto:{{ c.email }}">{{ c.email }}</a>{% else %}—{% endif %}</td>
```

Replace it with:
```html
            <td>
              {% if c.email %}
                <a href="mailto:{{ c.email }}">{{ c.email }}</a>
                {% if c.verification_status == 'valid' %}
                  <span title="Verified by Hunter.io" style="color:#4caf50;font-size:0.8rem;margin-left:4px;">✓ Verified</span>
                {% elif c.verification_status == 'accept_all' %}
                  <span title="Server accepts all mail — may not be monitored" style="color:#f0a500;font-size:0.8rem;margin-left:4px;">~ Accept All</span>
                {% elif c.verification_status == 'invalid' %}
                  <span title="Invalid email — likely to bounce" style="color:#e05a5a;font-size:0.8rem;margin-left:4px;">✗ Invalid</span>
                {% endif %}
              {% else %}—{% endif %}
            </td>
```

- [ ] **Step 2: Verify template renders**

Visit any prospect profile page with contacts in the browser. Contacts from Hunter with a `verification_status` should now show a badge next to their email. Contacts without one show no badge (unverified).

- [ ] **Step 3: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/templates/ro/profile_view.html"
git commit -m "feat: add email verification badges to prospect profile contacts table"
```

---

## Task 8: UI — Hunter usage widget + result badges in search.html

**Files:**
- Modify: `Owner Inbox/templates/ro/search.html`

- [ ] **Step 1: Add usage widget after the search form**

Find this line in `search.html` (around line 69):
```html
</form>
```
(The closing `</form>` tag of the search form — just before the `<!-- Running indicator -->` comment.)

Insert after it:
```html

<!-- Hunter.io usage widget -->
<div id="hunterUsageWidget" style="margin:12px 0 4px 0; font-size:0.82rem; color:var(--text-muted);">
  <span id="hunterUsageText">Loading Hunter credits…</span>
</div>
<script>
fetch('/ro/hunter/usage')
  .then(r => r.json())
  .then(d => {
    const el = document.getElementById('hunterUsageText');
    const sl = d.searches_left ?? 0;
    const vl = d.verifications_left ?? 0;
    const color = sl < 10 ? 'var(--warning, #f0a500)' : 'var(--text-muted)';
    el.style.color = color;
    el.textContent = `Hunter: ${sl} searches left · ${vl} verifications left`;
  })
  .catch(() => {
    document.getElementById('hunterUsageText').textContent = '';
  });
</script>

```

- [ ] **Step 2: Add Hunter badges to result cards**

Find this block in `search.html` (around line 137):
```html
            <div class="result-card {% if already_saved %}result-card-saved{% endif %}">
                <div class="result-title">
```

Replace just the `result-card` div opening line with:
```html
            <div class="result-card {% if already_saved %}result-card-saved{% endif %} {% if r.get('hunter_enriched') %}result-card-hunter-enriched{% endif %}">
                <div class="result-title">
```

Then find the `result-title` div content. Locate where the title/name is rendered and add a badge. Find:
```html
                <div class="result-title">
```
And add after the title text (look for `r.title` or `r.get('title')` in that block) — insert this after the title span/text inside `result-title`:
```html
                  {% if r.get('hunter_enriched') %}
                    <span style="display:inline-block;margin-left:6px;padding:1px 6px;border-radius:4px;background:#1a3a2a;color:#4caf50;font-size:0.72rem;font-weight:600;vertical-align:middle;">✓ Hunter</span>
                  {% elif r.get('hunter_only') %}
                    <span style="display:inline-block;margin-left:6px;padding:1px 6px;border-radius:4px;background:#1a2a3a;color:#6ab4f0;font-size:0.72rem;font-weight:600;vertical-align:middle;">Hunter</span>
                  {% endif %}
```

- [ ] **Step 3: Verify visually**

Run a search in the browser. You should see:
- Usage widget below the form with credit counts
- Green "✓ Hunter" badge on double-verified results
- Blue "Hunter" badge on Hunter-only results

- [ ] **Step 4: Commit**

```bash
cd "/home/ssinjin/Cyber-Network/RO-Marketing-Tools"
git add "Owner Inbox/templates/ro/search.html"
git commit -m "feat: add Hunter usage widget and result badges to search page"
```

---

## Final Verification

- [ ] Restart app and confirm no import errors: `python3 app.py`
- [ ] Visit `/ro/search` — usage widget loads, search returns merged results in correct order
- [ ] Run a search, confirm Hunter-enriched results appear first with green badge
- [ ] Visit a prospect profile, click "Find Contacts" — contacts appear with verification badges
- [ ] Run `python3 hunter_batch_finder.py --limit 2` — processes 2 prospects, prints summary with credit usage
