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
