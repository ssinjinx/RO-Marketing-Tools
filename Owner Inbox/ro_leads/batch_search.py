import sqlite3
import os
import time
import requests

APIFY_TOKEN = os.environ.get("APIFY_TOKEN", "")
DB_PATH = os.path.join(os.path.dirname(__file__), "ro_leads.db")

BUSINESS_TYPES = [
    "brewery",
    "restaurant and bar",
    "HVAC contractor",
    "auto body shop",
    "laser cutting",
    "welding shop",
    "hospital",
    "biotech lab",
    "construction company",
    "food processing",
]

INDUSTRY_PRODUCTS = {
    "brewery": "CO2 bulk systems, CO2 cylinders, Nitrogen, Dry ice",
    "restaurant": "CO2 cylinders, Dry ice",
    "bar": "CO2 cylinders, Dry ice",
    "hvac": "Nitrogen, Welding supplies",
    "auto body": "CO2, Argon, Welding supplies",
    "laser": "Oxygen, Nitrogen, Laser gas delivery systems",
    "welding": "Oxygen, Acetylene, Argon, Welding supplies",
    "hospital": "Medical O2, Medical N2, Bulk cryogenic systems",
    "biotech": "Specialty gases, LN2 systems, Cryogenic equipment",
    "lab": "Specialty gases, High-purity gases, LN2 systems",
    "construction": "Oxygen, Acetylene, Welding supplies",
    "food": "CO2 cylinders, Dry ice, Nitrogen",
}

CONTACT_TITLES = {
    "brewery": "Head Brewer / Owner",
    "restaurant": "Owner / General Manager",
    "bar": "Owner / General Manager",
    "hvac": "Owner / Operations Manager",
    "auto body": "Shop Owner / Manager",
    "laser": "Plant Manager / Operations Manager",
    "welding": "Shop Owner / Welding Supervisor",
    "hospital": "Facilities Director / Biomedical Engineering Director",
    "biotech": "Lab Manager / Facilities Director",
    "lab": "Lab Manager",
    "construction": "Project Manager / Owner",
    "food": "Plant Manager / Purchasing Manager",
}


def get_products(business_type):
    bt = business_type.lower()
    for key, val in INDUSTRY_PRODUCTS.items():
        if key in bt:
            return val
    return "Compressed gases, Welding supplies"


def get_contact_title(business_type):
    bt = business_type.lower()
    for key, val in CONTACT_TITLES.items():
        if key in bt:
            return val
    return "Owner / Manager"


def run_apify_actor(search_string):
    url = f"https://api.apify.com/v2/acts/compass~crawler-google-places/run-sync-get-dataset-items"
    params = {"token": APIFY_TOKEN}
    payload = {
        "searchStringsArray": [search_string],
        "maxCrawledPlacesPerSearch": 10,
        "language": "en",
        "exportPlaceUrls": False,
    }
    response = requests.post(url, json=payload, params=params, timeout=300)
    response.raise_for_status()
    return response.json()


def insert_prospects(conn, results, business_type):
    saved = 0
    skipped = 0
    products = get_products(business_type)
    contact_title = get_contact_title(business_type)

    for place in results:
        name = place.get("title") or place.get("name") or ""
        address = place.get("address") or place.get("street") or ""
        phone = place.get("phone") or place.get("phoneUnformatted") or ""
        website = place.get("website") or place.get("url") or ""
        industry = business_type

        if not name:
            skipped += 1
            continue

        # Check for duplicate by business_name + city
        existing = conn.execute(
            "SELECT id FROM prospects WHERE business_name = ? AND city = ?",
            (name, "Jacksonville"),
        ).fetchone()

        if existing:
            skipped += 1
            continue

        conn.execute(
            """INSERT OR IGNORE INTO prospects
               (business_name, address, phone, website, industry, state, city, ro_products, suggested_contact_title, status)
               VALUES (?, ?, ?, ?, ?, 'FL', 'Jacksonville', ?, ?, 'new')""",
            (name, address, phone, website, industry, products, contact_title),
        )
        saved += 1

    conn.commit()
    return saved, skipped


def main():
    conn = sqlite3.connect(DB_PATH)
    total_saved = 0
    total = len(BUSINESS_TYPES)

    for idx, business_type in enumerate(BUSINESS_TYPES, 1):
        search_string = f"{business_type} in Jacksonville FL"
        try:
            results = run_apify_actor(search_string)
            result_count = len(results)
            saved, skipped = insert_prospects(conn, results, business_type)
            total_saved += saved
            dup_note = f", {skipped} duplicates skipped" if skipped > 0 else ""
            print(f"[{idx}/{total}] {search_string} → {result_count} results, {saved} saved{dup_note}")
        except Exception as e:
            print(f"[{idx}/{total}] {search_string} → ERROR: {e}")

    conn.close()
    print(f"\nDone. Total saved: {total_saved} prospects")


if __name__ == "__main__":
    main()
