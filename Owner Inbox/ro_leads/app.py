import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from apify_client import ApifyClient
from database import get_db, init_db


def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    os.environ.setdefault(key.strip(), val.strip())


load_env()

app = Flask(__name__)
app.secret_key = "ro-leads-secret-2024"

# ── Constants ──────────────────────────────────────────────────────────────────

SERVICE_STATES = ["DE", "FL", "GA", "MD", "NJ", "NC", "PA", "SC", "VA"]

SERVICE_CITIES = [
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

DEFAULT_PRODUCTS = ["Compressed gases", "Welding supplies"]
DEFAULT_TITLE = "Owner / Operations Manager"

STATUS_OPTIONS = ["new", "contacted", "qualified", "not_a_fit"]


def match_products(industry: str) -> list:
    if not industry:
        return DEFAULT_PRODUCTS
    lower = industry.lower()
    for key, products in INDUSTRY_PRODUCTS.items():
        if key in lower:
            return products
    return DEFAULT_PRODUCTS


def match_title(industry: str) -> str:
    if not industry:
        return DEFAULT_TITLE
    lower = industry.lower()
    for key, title in CONTACT_TITLES.items():
        if key in lower:
            return title
    return DEFAULT_TITLE


# ── Search ─────────────────────────────────────────────────────────────────────

def search_businesses(business_type: str, area: str) -> list:
    token = os.environ.get('APIFY_API_TOKEN', '')
    if not token:
        return [{"error": "APIFY_API_TOKEN not set"}]

    try:
        client = ApifyClient(token)
        run_input = {
            "searchStringsArray": [f"{business_type} in {area}"],
            "maxCrawledPlacesPerSearch": 10,
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
        return results
    except Exception as e:
        return [{"error": str(e)}]


# ── Routes: Tab 1 — Roberts Oxygen Info ───────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("ro_info"))


@app.route("/ro-info")
def ro_info():
    return render_template("ro_info.html", active="ro_info")


# ── Routes: Tab 2 — Prospect Search ───────────────────────────────────────────

@app.route("/search", methods=["GET", "POST"])
def search():
    results = None
    business_type = ""
    area = ""
    if request.method == "POST":
        business_type = request.form.get("business_type", "").strip()
        area = request.form.get("area", "").strip()
        if business_type and area:
            results = search_businesses(business_type, area)
        else:
            flash("Please enter a business type and select an area.", "error")
    return render_template(
        "search.html",
        active="search",
        results=results,
        business_type=business_type,
        area=area,
        service_states=SERVICE_STATES,
        service_cities=SERVICE_CITIES,
    )


@app.route("/search/save", methods=["POST"])
def save_search_result():
    business_name = request.form.get("business_name", "").strip()
    website = request.form.get("website", "").strip()
    snippet = request.form.get("snippet", "").strip()
    industry = request.form.get("industry", "").strip()
    area = request.form.get("area", "").strip()
    address = request.form.get("address", "").strip() or snippet
    phone = request.form.get("phone", "").strip()
    category = request.form.get("category", "").strip()

    if not business_name:
        flash("Business name is required.", "error")
        return redirect(url_for("search"))

    # Attempt to parse city/state from area
    city, state = "", ""
    if "," in area:
        parts = area.split(",", 1)
        city = parts[0].strip()
        state = parts[1].strip()
    else:
        state = area.strip()

    effective_industry = industry or category
    products = match_products(effective_industry)
    title = match_title(effective_industry)

    db = get_db()
    db.execute(
        """INSERT INTO prospects
           (business_name, address, phone, website, industry, city, state,
            ro_products, suggested_contact_title, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            business_name,
            address,
            phone,
            website,
            effective_industry,
            city,
            state,
            ", ".join(products),
            title,
            "",
        ),
    )
    db.commit()
    db.close()
    flash(f"'{business_name}' saved to prospects.", "success")
    return redirect(url_for("search"))


# ── Routes: Tab 3 — Customer Profiles ─────────────────────────────────────────

@app.route("/profiles")
def profiles():
    db = get_db()
    prospects = db.execute(
        "SELECT * FROM prospects ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return render_template("profiles.html", active="profiles", prospects=prospects)


@app.route("/profiles/<int:prospect_id>")
def profile_view(prospect_id):
    db = get_db()
    prospect = db.execute(
        "SELECT * FROM prospects WHERE id = ?", (prospect_id,)
    ).fetchone()
    contacts = db.execute(
        "SELECT * FROM contacts WHERE prospect_id = ? ORDER BY name", (prospect_id,)
    ).fetchall()
    db.close()
    if not prospect:
        flash("Prospect not found.", "error")
        return redirect(url_for("profiles"))
    return render_template(
        "profile_view.html",
        active="profiles",
        prospect=prospect,
        contacts=contacts,
        status_options=STATUS_OPTIONS,
    )


@app.route("/profiles/<int:prospect_id>/edit", methods=["POST"])
def profile_edit(prospect_id):
    f = request.form
    db = get_db()
    db.execute(
        """UPDATE prospects SET
           business_name=?, address=?, phone=?, website=?, industry=?,
           city=?, state=?, ro_products=?, suggested_contact_title=?,
           status=?, notes=?, updated_at=datetime('now')
           WHERE id=?""",
        (
            f.get("business_name"), f.get("address"), f.get("phone"),
            f.get("website"), f.get("industry"), f.get("city"), f.get("state"),
            f.get("ro_products"), f.get("suggested_contact_title"),
            f.get("status"), f.get("notes"), prospect_id,
        ),
    )
    db.commit()
    db.close()
    flash("Prospect updated.", "success")
    return redirect(url_for("profile_view", prospect_id=prospect_id))


@app.route("/profiles/<int:prospect_id>/delete", methods=["POST"])
def profile_delete(prospect_id):
    db = get_db()
    db.execute("DELETE FROM prospects WHERE id = ?", (prospect_id,))
    db.commit()
    db.close()
    flash("Prospect deleted.", "success")
    return redirect(url_for("profiles"))


@app.route("/profiles/add", methods=["GET", "POST"])
def profile_add():
    if request.method == "POST":
        f = request.form
        industry = f.get("industry", "")
        products = f.get("ro_products") or ", ".join(match_products(industry))
        contact_title = f.get("suggested_contact_title") or match_title(industry)
        db = get_db()
        db.execute(
            """INSERT INTO prospects
               (business_name, address, phone, website, industry, city, state,
                ro_products, suggested_contact_title, status, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f.get("business_name"), f.get("address"), f.get("phone"),
                f.get("website"), industry, f.get("city"), f.get("state"),
                products, contact_title, f.get("status", "new"), f.get("notes"),
            ),
        )
        db.commit()
        db.close()
        flash("Prospect added.", "success")
        return redirect(url_for("profiles"))
    return render_template(
        "profile_add.html",
        active="profiles",
        status_options=STATUS_OPTIONS,
        service_states=SERVICE_STATES,
    )


# ── Routes: Tab 4 — Contacts ───────────────────────────────────────────────────

@app.route("/contacts")
def contacts():
    db = get_db()
    rows = db.execute(
        """SELECT c.*, p.business_name
           FROM contacts c
           LEFT JOIN prospects p ON c.prospect_id = p.id
           ORDER BY c.name"""
    ).fetchall()
    db.close()
    return render_template("contacts.html", active="contacts", contacts=rows)


@app.route("/contacts/add", methods=["GET", "POST"])
def contact_add():
    db = get_db()
    if request.method == "POST":
        f = request.form
        db.execute(
            """INSERT INTO contacts
               (prospect_id, name, title, email, phone, linkedin_url, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                f.get("prospect_id") or None, f.get("name"), f.get("title"),
                f.get("email"), f.get("phone"), f.get("linkedin_url"), f.get("notes"),
            ),
        )
        db.commit()
        db.close()
        flash("Contact added.", "success")
        return redirect(url_for("contacts"))
    prospects = db.execute(
        "SELECT id, business_name FROM prospects ORDER BY business_name"
    ).fetchall()
    db.close()
    return render_template(
        "contact_add.html", active="contacts", prospects=prospects
    )


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    db = get_db()
    contact = db.execute(
        "SELECT * FROM contacts WHERE id = ?", (contact_id,)
    ).fetchone()
    if not contact:
        flash("Contact not found.", "error")
        return redirect(url_for("contacts"))
    if request.method == "POST":
        f = request.form
        db.execute(
            """UPDATE contacts SET
               prospect_id=?, name=?, title=?, email=?, phone=?,
               linkedin_url=?, notes=? WHERE id=?""",
            (
                f.get("prospect_id") or None, f.get("name"), f.get("title"),
                f.get("email"), f.get("phone"), f.get("linkedin_url"),
                f.get("notes"), contact_id,
            ),
        )
        db.commit()
        db.close()
        flash("Contact updated.", "success")
        return redirect(url_for("contacts"))
    prospects = db.execute(
        "SELECT id, business_name FROM prospects ORDER BY business_name"
    ).fetchall()
    db.close()
    return render_template(
        "contact_edit.html", active="contacts", contact=contact, prospects=prospects
    )


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def contact_delete(contact_id):
    db = get_db()
    db.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
    db.commit()
    db.close()
    flash("Contact deleted.", "success")
    return redirect(url_for("contacts"))


# ── Routes: Tab 5 — Pipeline ───────────────────────────────────────────────────

@app.route("/pipeline")
def pipeline():
    db = get_db()
    all_prospects = db.execute(
        "SELECT * FROM prospects ORDER BY updated_at DESC"
    ).fetchall()
    db.close()
    columns = {
        "new": [],
        "contacted": [],
        "qualified": [],
        "not_a_fit": [],
    }
    for p in all_prospects:
        status = p["status"] if p["status"] in columns else "new"
        columns[status].append(p)
    return render_template("pipeline.html", active="pipeline", columns=columns)


@app.route("/pipeline/move/<int:prospect_id>", methods=["POST"])
def pipeline_move(prospect_id):
    new_status = request.form.get("status")
    if new_status not in STATUS_OPTIONS:
        flash("Invalid status.", "error")
        return redirect(url_for("pipeline"))
    db = get_db()
    db.execute(
        "UPDATE prospects SET status=?, updated_at=datetime('now') WHERE id=?",
        (new_status, prospect_id),
    )
    db.commit()
    db.close()
    return redirect(url_for("pipeline"))


# ── Main ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(port=5001, debug=False)
