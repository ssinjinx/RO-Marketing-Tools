"""
competitor_monitor.py — Rex's weekly competitor intelligence script.

What it does:
  1. Loads competitor list from competitors.json
  2. Uses Firecrawl to map + extract each competitor site
  3. Saves snapshot to competitor_snapshots/<name>_YYYYMMDD.json
  4. Diffs against previous snapshot and logs changes
  5. Writes a human-readable report to reports/competitor_report_YYYYMMDD.txt

Run modes:
  python3 competitor_monitor.py           # run once immediately
  python3 competitor_monitor.py --watch   # run weekly every Monday at 8am

Requirements:
  pip install firecrawl-py schedule
"""

import os
import sys
import json
import time
import datetime
import difflib

# Load .env from same directory
def load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())

load_env()

BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
SNAPSHOTS_DIR  = os.path.join(BASE_DIR, 'competitor_snapshots')
REPORTS_DIR    = os.path.join(BASE_DIR, 'reports')
COMPETITORS_FILE = os.path.join(BASE_DIR, 'competitors.json')

os.makedirs(SNAPSHOTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)


def load_competitors() -> list:
    with open(COMPETITORS_FILE) as f:
        return json.load(f)['competitors']


def load_last_snapshot(name: str) -> dict:
    """Load the most recent snapshot for a competitor, or empty dict."""
    prefix = name.lower().replace(' ', '_')
    files = sorted([
        f for f in os.listdir(SNAPSHOTS_DIR)
        if f.startswith(prefix) and f.endswith('.json')
    ])
    if not files:
        return {}
    with open(os.path.join(SNAPSHOTS_DIR, files[-1])) as f:
        return json.load(f)


def save_snapshot(name: str, data: dict) -> str:
    prefix = name.lower().replace(' ', '_')
    date_str = datetime.datetime.now().strftime('%Y%m%d')
    filename = f"{prefix}_{date_str}.json"
    path = os.path.join(SNAPSHOTS_DIR, filename)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    return filename


def diff_snapshots(old: dict, new: dict) -> list:
    """Return list of human-readable change strings."""
    changes = []
    all_keys = set(old) | set(new)
    for key in sorted(all_keys):
        old_val = old.get(key, '')
        new_val = new.get(key, '')
        if old_val == new_val:
            continue
        if not old_val:
            changes.append(f'  + NEW [{key}]: {new_val[:200]}')
        elif not new_val:
            changes.append(f'  - REMOVED [{key}]')
        else:
            # Show a short diff of the text
            old_lines = old_val.splitlines()
            new_lines = new_val.splitlines()
            diff = list(difflib.unified_diff(old_lines, new_lines, lineterm='', n=1))
            if diff:
                changes.append(f'  ~ CHANGED [{key}]:')
                for line in diff[2:6]:  # Show up to 4 diff lines
                    changes.append(f'    {line}')
    return changes


def run_monitor():
    from firecrawl_client import snapshot_competitor

    today = datetime.datetime.now().strftime('%Y-%m-%d')
    report_lines = [
        f'Competitor Intelligence Report — {today}',
        '=' * 60,
        '',
    ]

    competitors = load_competitors()
    print(f'Running competitor monitor for {len(competitors)} competitors...')

    for i, comp in enumerate(competitors):
        name = comp['name']
        url  = comp['url']
        if i > 0:
            print(f'  Waiting 15s (rate limit)...')
            time.sleep(15)
        print(f'  Scanning {name} ({url})...')

        new_data = snapshot_competitor(url)

        if 'error' in new_data:
            report_lines.append(f'## {name}')
            report_lines.append(f'  ERROR: {new_data["error"]}')
            report_lines.append('')
            continue

        old_data = load_last_snapshot(name)
        changes  = diff_snapshots(old_data, new_data)
        filename = save_snapshot(name, new_data)

        report_lines.append(f'## {name}  ({url})')
        report_lines.append(f'   Snapshot: {filename}')

        if not old_data:
            report_lines.append('   Status: First snapshot — baseline established')
            for k, v in new_data.items():
                report_lines.append(f'   {k}: {v[:200]}')
        elif not changes:
            report_lines.append('   Status: No changes detected')
        else:
            report_lines.append(f'   Status: {len(changes)} change(s) detected')
            report_lines.extend(changes)

        report_lines.append('')

    # Write report file
    report_text = '\n'.join(report_lines)
    report_filename = f"competitor_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path = os.path.join(REPORTS_DIR, report_filename)
    with open(report_path, 'w') as f:
        f.write(report_text)

    print(f'\nReport saved: {report_path}')
    print(report_text)
    return report_path


if __name__ == '__main__':
    if '--watch' in sys.argv:
        import schedule
        import time
        print('Competitor monitor running in watch mode — fires every Monday at 08:00')
        schedule.every().monday.at('08:00').do(run_monitor)
        # Also run immediately on start
        run_monitor()
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_monitor()
