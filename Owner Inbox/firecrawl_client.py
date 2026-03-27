"""
Firecrawl integration for RO Marketing Tools.

Two use cases:
  1. Prospect website profiling — extract contact info + gas-usage signals
  2. Competitor intelligence — map + extract competitor sites for weekly diffs
"""

import os
from typing import Optional

_client = None


def get_client():
    global _client
    if _client is None:
        from firecrawl import Firecrawl
        api_key = os.environ.get('FIRECRAWL_API_KEY', '')
        if not api_key:
            raise RuntimeError('FIRECRAWL_API_KEY not set in .env')
        _client = Firecrawl(api_key=api_key)
    return _client


# ─── Use Case 1: Prospect Profiling ──────────────────────────────────────────

PROSPECT_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name":        {"type": "string",  "description": "Business name"},
        "phone":               {"type": "string",  "description": "Primary phone number"},
        "address":             {"type": "string",  "description": "Street address"},
        "city":                {"type": "string",  "description": "City"},
        "state":               {"type": "string",  "description": "State abbreviation (2 letters)"},
        "contact_name":        {"type": "string",  "description": "Owner or purchasing contact name if listed"},
        "contact_title":       {"type": "string",  "description": "Title of the contact person (Owner, Manager, etc.)"},
        "gas_signals":         {"type": "string",  "description": "Any mention of industrial gases, welding equipment, brewing systems, medical gas, CO2, oxygen, nitrogen, argon, acetylene, or gas cylinders"},
        "current_supplier":    {"type": "string",  "description": "Name of any current gas or industrial supply vendor mentioned"},
        "equipment_mentioned": {"type": "string",  "description": "Equipment that uses industrial gas: welders, fermenters, draft beer systems, CNC plasma cutters, medical equipment, laser cutters"},
        "business_type":       {"type": "string",  "description": "Type of business: brewery, restaurant, welding shop, auto body shop, hospital, HVAC, laser cutting, metal fabrication, etc."},
    },
    "required": []
}


def profile_prospect(website_url: str) -> dict:
    """
    Extract structured prospect data from a company website.
    Returns a dict with whatever fields Firecrawl could find.
    Empty/missing fields are omitted.
    """
    try:
        client = get_client()
        result = client.extract(
            [website_url],
            {
                'prompt': (
                    'Extract contact information and any signals about industrial gas usage '
                    'from this business website. Focus on: phone numbers, physical address, '
                    'owner or manager names, any equipment or processes that use industrial gases '
                    '(welding, brewing, medical, restaurants with draft beer, HVAC, manufacturing), '
                    'and any current gas or industrial supply vendors mentioned.'
                ),
                'schema': PROSPECT_SCHEMA,
            }
        )
        data = result.get('data', {}) if isinstance(result, dict) else {}
        # Strip empty strings and None values
        return {k: v for k, v in data.items() if v}
    except Exception as e:
        return {'error': str(e)}


# ─── Use Case 2: Competitor Intelligence ─────────────────────────────────────

COMPETITOR_SCHEMA = {
    "type": "object",
    "properties": {
        "service_areas":    {"type": "string", "description": "States, regions, or cities served"},
        "product_list":     {"type": "string", "description": "Gas types, cylinder sizes, and products offered"},
        "pricing_info":     {"type": "string", "description": "Any pricing, rates, delivery fees, or quote information visible"},
        "locations":        {"type": "string", "description": "Physical branch locations, distribution centers, or fill plants listed"},
        "recent_news":      {"type": "string", "description": "Any news, announcements, press releases, or recent updates"},
        "specializations":  {"type": "string", "description": "Any niche markets or specializations mentioned (medical, industrial, specialty gas, welding)"},
    },
    "required": []
}


def snapshot_competitor(competitor_url: str) -> dict:
    """
    Map a competitor site to find key pages, then extract structured intel.
    Returns a dict snapshot of the competitor's public-facing data.
    """
    try:
        client = get_client()

        # Step 1: map the site to find relevant pages
        map_result = client.map_url(
            competitor_url,
            params={'search': 'service area products pricing locations news about'}
        )
        urls = map_result.get('links', [])[:15] if isinstance(map_result, dict) else []

        # Always include the homepage
        if competitor_url not in urls:
            urls = [competitor_url] + urls[:14]

        if not urls:
            urls = [competitor_url]

        # Step 2: extract structured intel from those pages
        result = client.extract(
            urls,
            {
                'prompt': (
                    'Extract service areas, product lines, pricing information, physical locations, '
                    'and any recent news or announcements from this industrial gas supplier website.'
                ),
                'schema': COMPETITOR_SCHEMA,
            }
        )
        data = result.get('data', {}) if isinstance(result, dict) else {}
        return {k: v for k, v in data.items() if v}
    except Exception as e:
        return {'error': str(e)}


def search_prospects(query: str, limit: int = 10) -> list:
    """
    Search the web for prospects matching a query.
    Returns list of {url, title, snippet}.
    """
    try:
        client = get_client()
        result = client.search(query, params={'limit': limit})
        items = []
        for r in (result.get('data', []) if isinstance(result, dict) else []):
            items.append({
                'url':     r.get('url', ''),
                'title':   r.get('title', ''),
                'snippet': (r.get('markdown') or r.get('description') or '')[:400],
            })
        return items
    except Exception as e:
        return [{'error': str(e)}]
