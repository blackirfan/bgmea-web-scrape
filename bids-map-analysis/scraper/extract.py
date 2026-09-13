"""
Parses one factory detail page (mappedinbangladesh.org/factories/<id>) into a
flat record dict.

The page renders a hidden "pdfComponent" div (used for their own "Download
Details" PDF export) that contains every field from the General, Production,
ESG and Address tabs already flattened into one consistent
icon + label + value structure -- no tab-clicking required. Each field is:

    <div>                                  (field block)
      <img alt="icon" .../>
      <div class="mantine-Stack-root">     (stack)
        <p>Label Text</p>
        <div class="mantine-Flex-root">    (value container)
          <span>Value 1</span>
          <span>Value 2</span>
          ...
"""
import re

from bs4 import BeautifulSoup

LABEL_MAP = {
    "Factory Type": "factory_type",
    "Establishment Year": "establishment_year",
    "Premises Type": "premises_type",
    "Memberships": "memberships",
    "Building Safety Inspection": "building_safety_inspection",
    "Certifications": "certifications",
    "Workers": "workers",
    "No. of Sewing Lines": "sewing_lines",
    "No. of Sewing Machines": "sewing_machines",
    "No. of Jacquard Machines": "jacquard_machines",
    "No. of Manual Machines": "manual_machines",
    "Production Capacity": "production_capacity",
    "Products": "products",
    "Brands": "buyers_brands_agents",
    "Export Countries": "export_countries",
    "ETP": "etp",
    "Solar Panel Usage": "solar",
    "Platforms / Projects / Programs": "platforms_projects_programs",
    "Worker Facilities": "worker_facilities",
    "Workplace Committees": "workplace_committees",
    "Address": "address",
    "Nearby Medical Center": "nearby_medical_center",
    "Nearby Fire Station": "nearby_fire_station",
    "Nearby Police Station": "nearby_police_station",
}

# These labels have [name, distance] as two separate spans instead of a
# flat multi-value list -- combine as "name (distance)".
TWO_PART_NEARBY = {"Nearby Medical Center", "Nearby Fire Station", "Nearby Police Station"}

# Labels that mark the site's logged-out / no-data placeholder state.
LOGIN_MARKERS = ("Login", "Login or Register")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[+\d][\d\s\-]{6,}$")

# All columns written to the output spreadsheet, in order.
PLACEHOLDER_VALUES = {"Not Reported", "Not reported"}

# Columns that reflect real page content (excludes ids/urls/coords/meta).
DATA_COLUMNS = [
    "factory_type", "establishment_year", "premises_type", "memberships",
    "building_safety_inspection", "certifications",
    "workers", "production_capacity", "products",
    "buyers_brands_agents", "export_countries",
    "etp", "solar", "worker_facilities", "workplace_committees",
    "address", "contact_phone", "contact_email", "contact_website",
    "nearby_medical_center", "nearby_fire_station", "nearby_police_station",
]


def is_placeholder_heavy(record, threshold=10):
    """True if the page still looks like the un-loaded/empty skeleton."""
    n_placeholder = 0
    for col in DATA_COLUMNS:
        val = record.get(col, "")
        if not val or val in PLACEHOLDER_VALUES or "Not Reported" in val or "Not reported" in val:
            n_placeholder += 1
    return n_placeholder >= threshold


OUTPUT_COLUMNS = [
    "factory_id", "factory_url", "factory_name", "last_updated",
    "factory_type", "establishment_year", "premises_type", "memberships",
    "building_safety_inspection", "certifications",
    "workers", "sewing_lines", "sewing_machines", "jacquard_machines",
    "manual_machines", "production_capacity", "products",
    "buyers_brands_agents", "export_countries",
    "etp", "solar", "platforms_projects_programs", "worker_facilities",
    "workplace_committees",
    "address", "contact_phone", "contact_email", "contact_website",
    "nearby_medical_center", "nearby_fire_station", "nearby_police_station",
    "latitude", "longitude",
    "scrape_status", "scraped_at",
]


def extract_field_blocks(pdf_soup):
    """Return {label_text: [value_span_texts...]} for every field block found."""
    blocks = {}
    for div in pdf_soup.find_all("div"):
        img = div.find("img", attrs={"alt": "icon"}, recursive=False)
        if img is None:
            continue
        stack = None
        for child in div.find_all("div", recursive=False):
            if "mantine-Stack-root" in (child.get("class") or []):
                stack = child
                break
        if stack is None:
            continue
        ps = stack.find_all("p", recursive=False)
        if not ps:
            continue
        label = ps[0].get_text(strip=True)
        value_divs = stack.find_all("div", recursive=False)
        if not value_divs:
            continue
        spans = value_divs[0].find_all("span", recursive=False)
        values = [s.get_text(strip=True) for s in spans if s.get_text(strip=True)]
        if values:
            blocks.setdefault(label, values)
    return blocks


def classify_contact(values):
    phone = email = website = ""
    for v in values:
        if EMAIL_RE.match(v):
            email = v
        elif PHONE_RE.match(v.replace(" ", "")):
            phone = v
        else:
            website = v
    return phone, email, website


def extract_factory(driver):
    """Extract one factory record from the currently-loaded page. Returns dict."""
    title = driver.title or ""
    name = title.split(" | ")[0].strip() if title else ""
    html = driver.page_source

    record = {col: "" for col in OUTPUT_COLUMNS}
    record["factory_name"] = name

    soup = BeautifulSoup(html, "html.parser")
    pdf = soup.find("div", id="pdfComponent")

    if pdf is None:
        record["scrape_status"] = "no_pdf_component"
        return record

    lu = pdf.find(string=re.compile(r"^Last Updated:"))
    record["last_updated"] = lu.split(":", 1)[1].strip() if lu else ""

    blocks = extract_field_blocks(pdf)

    for label, col in LABEL_MAP.items():
        if label in TWO_PART_NEARBY:
            continue
        values = blocks.get(label, [])
        record[col] = "; ".join(dict.fromkeys(values))

    for label in TWO_PART_NEARBY:
        col = LABEL_MAP[label]
        values = blocks.get(label, [])
        if not values:
            record[col] = ""
        elif len(values) == 1:
            record[col] = values[0]
        else:
            record[col] = f"{values[0]} ({values[1]})"

    phone, email, website = classify_contact(blocks.get("Contact Details", []))
    record["contact_phone"] = phone
    record["contact_email"] = email
    record["contact_website"] = website

    text = soup.get_text(" ", strip=True)
    logged_out = any(m in text for m in LOGIN_MARKERS) and "Logout" not in text

    field_count = len(blocks)
    if logged_out:
        record["scrape_status"] = "login_required"
    elif field_count == 0:
        record["scrape_status"] = "empty"
    elif field_count < 4:
        record["scrape_status"] = "sparse"
    else:
        record["scrape_status"] = "ok"

    return record
