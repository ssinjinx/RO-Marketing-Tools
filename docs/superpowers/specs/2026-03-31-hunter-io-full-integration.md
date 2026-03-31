# Hunter.io Full Integration

**Date:** 2026-03-31
**Status:** Approved

---

## Overview

Expand the existing Hunter.io integration from a single domain search helper into a full prospecting and contact verification pipeline. Four new helper functions, modifications to three existing routes, a new usage API endpoint, and a complete rewrite of `hunter_batch_finder.py`.

---

## 1. Hunter Helper Functions

Add four functions to `app.py` alongside the existing `find_with_hunter()`:

### `hunter_verify_email(email) → dict`
- Calls `GET https://api.hunter.io/v2/email-verifier?email=<email>&api_key=<key>`
- Returns `{"status": str, "score": int}` where status is one of: `valid`, `invalid`, `accept_all`, `webmail`, `disposable`, `unknown`
- Returns `{"status": "unknown", "score": 0}` on error
- Green checkmark shown in UI when status is `valid` or `accept_all`

### `hunter_find_email(first_name, last_name, domain) → dict | None`
- Calls `GET https://api.hunter.io/v2/email-finder?domain=<domain>&first_name=<fn>&last_name=<ln>&api_key=<key>`
- Returns `{"email": str, "confidence": int}` or `None` if not found / error
- Used as fallback when domain search returns no named contacts

### `hunter_discover(keywords, location, limit=10) → list[dict]`
- Calls `GET https://api.hunter.io/v2/discover?keywords=<kw>&location=<loc>&limit=<n>&api_key=<key>`
- Returns list of `{"name": str, "domain": str, "website": str, "industry": str, "size": str}`
- Returns `[]` on error or missing API key

### `hunter_account_info() → dict`
- Calls `GET https://api.hunter.io/v2/account?api_key=<key>`
- Returns `{"searches_used": int, "searches_left": int, "verifications_used": int, "verifications_left": int}`
- Returns zeroed dict on error

---

## 2. Database Schema Changes

Add two columns to `ro_contacts`:

```sql
ALTER TABLE ro_contacts ADD COLUMN verified INTEGER DEFAULT 0;
ALTER TABLE ro_contacts ADD COLUMN verification_status TEXT DEFAULT 'unverified';
```

Applied via a migration check in `get_db()` (same pattern as existing migrations in the app).

---

## 3. Find Contacts Flow (modified `ro_find_contacts`)

**Route:** `POST /ro/profiles/<prospect_id>/find-contacts`

New flow:
1. Hunter domain search → up to 3 contacts (existing)
2. If no **named** contacts returned → `hunter_find_email()` fallback using prospect name parts + domain
3. Web scraper fallback (existing, unchanged)
4. Email guesser fallback (existing, unchanged)
5. **For every contact found** (regardless of source): call `hunter_verify_email(email)` and save `verified` + `verification_status` to `ro_contacts`

Response JSON gains `verified` and `verification_status` fields per contact:
```json
{
  "contacts": [
    {"id": 1, "email": "john@acme.com", "name": "John Smith", "title": "Owner",
     "verified": true, "verification_status": "valid"}
  ],
  "source": "hunter"
}
```

---

## 4. Search Page — Apify + Hunter Discover Merge

**Modified:** `_run_search_job()` and `ro_search()`

### Parallel execution
When a search is submitted, two threads run simultaneously:
- Thread A: Apify Google Places (existing, unchanged)
- Thread B: `hunter_discover(keywords=business_type, location=area)`

Both results are stored in `_search_jobs[job_id]`. Merge happens when results are read.

### Merge logic
1. Build a lookup from Hunter results keyed by domain (stripped of `www.`)
2. For each Apify result: check if its website domain matches a Hunter result
   - Match → set `hunter_enriched=True`, attach Hunter `industry` and `size` data
   - No match → `hunter_enriched=False`
3. Hunter-only results (not in Apify) appended at the end with `source='hunter'`

### Result ordering
1. **Hunter-enriched** results first (found in both sources — double-verified)
2. **Apify-only** results second
3. **Hunter-only** results last

### Usage widget
- New route: `GET /ro/hunter/usage` → returns `hunter_account_info()` as JSON
- Search page fetches this on load via `fetch('/ro/hunter/usage')`
- Displays: `Hunter: 47 searches left · 312 verifications left`
- Widget turns yellow (`warning` class) when searches remaining < 10

---

## 5. `hunter_batch_finder.py` (complete rewrite)

Standalone script for batch processing prospects without using the web UI.

### Flow (10 prospects per run)
1. Query DB for prospects with `status='new'` that have a `website`, limit 10
2. For each prospect:
   a. Call Hunter domain search → collect contacts
   b. If no named contacts → call `hunter_find_email()` with prospect name parts
   c. Verify each found email via `hunter_verify_email()`
   d. Insert contacts into `ro_contacts` with `verified`/`verification_status`
   e. Update prospect `status` to `'profiled'`
3. Print summary: prospects processed, contacts found, contacts verified, Hunter credits consumed

### Credit tracking
- Call `hunter_account_info()` before and after batch
- Print credits used in summary
- Abort with warning if fewer than 5 searches remain before starting

### Usage
```bash
python3 hunter_batch_finder.py         # process 10 prospects
python3 hunter_batch_finder.py --limit 5  # process 5 prospects
```

---

## 6. UI Changes

### Contact display (profile view template)
- Next to each email address, show:
  - ✅ green checkmark + "Verified" if `verification_status` in `['valid', 'accept_all']`
  - ⚠️ yellow icon + "Accept All" if `verification_status == 'accept_all'` (deliverable but unconfirmed)
  - ❌ red icon + "Invalid" if `verification_status == 'invalid'`
  - No badge if `verification_status == 'unverified'`

### Search results (search template)
- Hunter-enriched results get a small "✓ Hunter" badge
- Hunter-only results get a "Hunter" source badge
- Hunter usage widget below the search form

---

## Files Changed

| File | Change |
|------|--------|
| `Owner Inbox/app.py` | Add 4 helper functions, modify `ro_find_contacts`, modify `_run_search_job`, add `GET /ro/hunter/usage` route, add DB migration for new columns |
| `Owner Inbox/hunter_batch_finder.py` | Complete rewrite with real API calls |
| `Owner Inbox/templates/ro/profile_view.html` | Add verification badges next to emails |
| `Owner Inbox/templates/ro/search.html` | Add Hunter usage widget, Hunter badges on results |

---

## Error Handling

- All Hunter API calls wrapped in try/except — failures degrade gracefully (return empty/default values, never crash the main flow)
- Hunter API errors logged to stderr in batch script
- If Hunter account has 0 searches left, `hunter_discover` and `find_with_hunter` return `[]` immediately (checked via `hunter_account_info()` cached for 5 minutes)
