# BGMEA + Mapped in Bangladesh RMG Factory Data Collection

## Purpose

Build an automated, reproducible and resumable data collection pipeline that populates an existing Excel spreadsheet with Bangladesh RMG factory information.

The primary source is:

- BGMEA General Member List:
  https://www.bgmea.com.bd/page/member-list

The secondary validation source is:

- Mapped in Bangladesh (MiB):
  https://mappedinbangladesh.org/

The output must populate the following columns:

| Column |
|---|
| Name of factory |
| BGMEA registration no. |
| Address of factory |
| Factory type (woven, knit, both) |
| management |
| Employee_male |
| Employee_female |
| No. of machines |
| Production capacity |

The objective is to obtain the information primarily from BGMEA and use MiB to validate, enrich and flag discrepancies.

---

# 1. Core Rules

## 1.1 Never invent data

Never generate, estimate or infer a factory attribute when the source does not provide it.

If a field cannot be verified:

- leave it blank
- record the reason in the audit dataset
- optionally record the source URL

Do NOT use:

- `0`
- `N/A`
- guessed values
- calculated estimates

unless the source explicitly provides that value.

---

## 1.2 Preserve the user's Excel structure

Before modifying the workbook:

1. Detect the input Excel file.
2. Inspect:
   - workbook name
   - sheet names
   - headers
   - existing rows
   - formatting
   - formulas
   - merged cells
3. Do not delete existing sheets.
4. Do not rename the user's columns unless explicitly instructed.
5. Preserve existing formatting where possible.
6. Save a new output workbook rather than destroying the original.

Example:

```text
input/
    factories.xlsx

output/
    factories_completed.xlsx
```

---

# 2. Target Data Model

Internally normalize every factory into the following structure:

```python
FactoryRecord = {
    "factory_name": None,
    "bgmea_registration_no": None,
    "factory_address": None,
    "factory_type": None,
    "management": None,
    "employee_male": None,
    "employee_female": None,
    "number_of_machines": None,
    "production_capacity": None,

    "bgmea_url": None,
    "mib_url": None,

    "bgmea_match_status": None,
    "mib_match_status": None,
    "validation_status": None,

    "source_conflicts": [],
    "confidence_score": None,
    "last_checked": None
}
```

Do not expose internal fields in the final user Excel unless requested.

Maintain a separate audit file containing these fields.

---

# 3. Source Priority

Use the following priority:

```text
1. BGMEA
2. Mapped in Bangladesh
3. Other authoritative source only if explicitly enabled
```

BGMEA is the primary source for:

- factory name
- BGMEA registration number
- BGMEA address
- factory/product type
- machines
- production/export capacity
- management/contact information

MiB is primarily used for:

- factory identity validation
- factory type validation
- worker information
- address/location validation
- factory existence/status validation
- identifying possible duplicate/unit records

MiB should not automatically overwrite BGMEA values.

---

# 4. BGMEA Collection

## 4.1 General Member List

Start from:

```text
https://www.bgmea.com.bd/page/member-list
```

The page is paginated.

Do not assume a fixed number of pages.

Determine the total number of pages dynamically from the pagination controls.

Current examples show approximately 214/215 pages and more than 4,000 general members, but this may change.

Therefore:

```python
discover_pagination()
```

must be implemented dynamically.

---

# 5. BGMEA Pagination

For every page:

```text
/page/member-list
/page/member-list?page=2
/page/member-list?page=3
...
```

Extract:

- Member/Company Name
- BGMEA Reg No
- Contact Person
- Email
- Details URL

Example normalized record:

```json
{
    "factory_name": "3A Fashions Ltd.",
    "bgmea_registration_no": "5161",
    "contact_person": "Atique Hossain",
    "email": "info@3afl.com",
    "bgmea_url": "..."
}
```

The summary page currently exposes the factory/company name and BGMEA registration number directly.

---

# 6. BGMEA Detail Page

For every member:

1. Follow the `Details` link.
2. Parse the complete factory/member information.
3. Map fields to the internal schema.

Do not assume the HTML structure will remain unchanged.

Use resilient selectors.

Preferred extraction order:

```text
CSS selectors
↓
HTML semantic structure
↓
label/value relationships
↓
table rows
↓
regex fallback
```

Avoid relying on:

```python
soup.find_all("td")[17]
```

or other positional selectors.

---

# 7. Field Mapping

Normalize source labels into these target fields.

## Factory name

Possible source labels:

```text
Member/Company Name
Company Name
Factory Name
Unit Name
```

Map to:

```text
factory_name
```

---

## BGMEA registration number

Possible labels:

```text
BGMEA Reg No
Registration No
BGMEA Registration No
Reg No
```

Map to:

```text
bgmea_registration_no
```

Preserve registration numbers as strings.

Do not convert them into floating point numbers.

Example:

```text
60
95
1095
5161
```

must remain:

```text
"60"
"95"
"1095"
"5161"
```

---

# 8. Address

Look for:

```text
Factory Address
Address
Factory/Unit Address
Mailing Address
Registered Address
```

Prefer the physical factory address over a corporate/head-office address.

If both exist:

```text
factory_address = physical factory address
```

Do not concatenate unrelated addresses.

---

# 9. Factory Type

Normalize all source values to exactly one of:

```text
woven
knit
both
```

Possible source values:

```text
Woven
Woven Garment
Knit
Knit Garment
Knitwear
Woven, Knit
Woven Garment, Knit Garment
Composite
```

Mapping:

```python
if woven and knit:
    "both"

elif woven:
    "woven"

elif knit:
    "knit"
```

If only "Sweater" is available, do not automatically classify it unless the source methodology explicitly supports treating sweater as knit.

If classification is uncertain:

```text
factory_type = blank
```

and record:

```text
validation_note = "Factory type could not be confidently normalized"
```

---

# 10. Management

Search for source fields such as:

```text
Management
Management Type
Ownership
Managing Director
Director
CEO
Chairman
Contact Person
```

Do not confuse a person's name with management type.

If the target Excel column means ownership/management category, preserve the source terminology.

For example:

```text
Private
Public
Joint Venture
Foreign
Local
```

If the source only gives a person's name and the meaning of `management` is unclear, do not invent a management classification.

---

# 11. Employee Data

Extract:

```text
Employee_male
Employee_female
```

Look for:

```text
Number of Workers
Workers
Male Workers
Female Workers
Male
Female
Employees
```

MiB may provide worker information separately.

For example:

```text
Male - 752
Female - 2,858
```

Normalize:

```text
Male = 752
Female = 2858
```

Store numeric values as integers.

Remove:

```text
,
spaces
workers
persons
```

during normalization.

Example:

```text
"2,858 workers"
```

becomes:

```text
2858
```

---

# 12. Machine Count

Look for:

```text
Number of Machines
Machines
No. of Machines
Machine Number
```

Normalize:

```text
"1,250"
```

to:

```text
1250
```

Store as integer.

Never estimate machine counts from employees.

---

# 13. Production Capacity

Look for:

```text
Production Capacity
Export Capacity
Capacity
Production
Annual Production Capacity
```

Do not normalize away the unit.

For example:

```text
500,000 pcs/month
2,000,000 pcs/year
50,000 dozen/month
```

should remain understandable.

If the source gives:

```text
Capacity = 500000
Unit = pcs/month
```

store:

```text
500000 pcs/month
```

Do not convert monthly capacity to annual capacity unless explicitly requested.

---

# 14. Mapped in Bangladesh Collection

Use:

```text
https://mappedinbangladesh.org/
```

MiB contains an RMG factory directory and factory search functionality.

Use it as a validation/enrichment source.

Do not blindly scrape every dynamic UI element if the site exposes a structured endpoint.

First inspect:

```text
HTML
JavaScript
network requests
API endpoints
embedded JSON
```

If an official structured endpoint exists, prefer that over browser automation.

---

# 15. MiB Factory Discovery

MiB factory records may be discovered through:

```text
Factory Directory
Search
District
Police Station / Thana
Upazila
Factory name
```

Build a MiB master dataset before matching wherever practical.

Example:

```python
mib_records = [
    {
        "factory_name": "...",
        "factory_type": "...",
        "workers_male": ...,
        "workers_female": ...,
        "address": "...",
        "mib_url": "..."
    }
]
```

---

# 16. Entity Matching

Factory names will not always match exactly.

Example:

```text
ABC Garments Ltd
ABC Garments Limited
ABC GARMENTS LTD.
ABC Garments Ltd. (Unit-2)
```

Therefore implement multi-stage matching.

## Stage 1 — Exact normalized name

Normalize:

```python
def normalize_name(name):
    name = name.lower()
    name = remove_punctuation(name)
    name = normalize_whitespace(name)

    replacements = {
        "limited": "ltd",
        "private": "pvt",
        "company": "co"
    }

    return name
```

Then compare.

---

# 17. Unit-Aware Matching

Do not incorrectly merge:

```text
ABC Garments Ltd
ABC Garments Ltd Unit-2
ABC Garments Ltd Unit-3
```

Unit identifiers are important.

Normalize:

```text
unit 1
unit-1
unit 01
u-1
(unit-1)
```

into:

```text
unit_1
```

Use unit information as a matching feature.

---

# 18. Fuzzy Matching

Use fuzzy matching only after exact matching fails.

Recommended libraries:

```text
rapidfuzz
```

Example:

```python
from rapidfuzz import fuzz

score = fuzz.token_set_ratio(
    bgmea_name,
    mib_name
)
```

Suggested confidence thresholds:

```text
>= 95       automatic match
90–94       probable match
80–89       manual review
< 80        no match
```

These are starting thresholds, not absolute truth.

---

# 19. Address Matching

Use address as a secondary matching feature.

Normalize:

```text
road
rd
road no
road number
```

and common location spellings.

Examples:

```text
Gazipur
Gazipura
Gazipur District
```

should be compared carefully.

Do not use aggressive replacement that changes actual location names.

---

# 20. Composite Matching Score

Use a weighted score.

Example:

```python
score = (
    name_score * 0.55 +
    address_score * 0.20 +
    location_score * 0.10 +
    type_score * 0.05 +
    registration_score * 0.10
)
```

If BGMEA registration number is unavailable in MiB, redistribute the weight.

Example:

```python
score = (
    name_score * 0.65 +
    address_score * 0.20 +
    location_score * 0.10 +
    type_score * 0.05
)
```

Never consider fuzzy name similarity alone sufficient when multiple candidates are close.

---

# 21. Duplicate Detection

Detect:

```text
same BGMEA registration number
same normalized factory name
same factory + unit
same address + similar factory name
```

Create duplicate groups.

Example:

```text
duplicate_group_id
```

Do not silently delete duplicates.

---

# 22. Validation Logic

For every matched BGMEA/MiB record:

Compare:

```text
factory name
address
factory type
male workers
female workers
machines
production capacity
```

Create:

```python
validation_status
```

Possible values:

```text
MATCHED
MATCHED_WITH_DIFFERENCES
BGMEA_ONLY
MIB_ONLY
AMBIGUOUS_MATCH
POSSIBLE_DUPLICATE
```

---

# 23. Source Precedence

When two sources conflict:

## Identity

Prefer:

```text
BGMEA registration number
```

for BGMEA identity.

## Factory name

Prefer BGMEA for the primary output.

Use MiB to flag differences.

## Factory type

If BGMEA and MiB disagree:

```text
do not automatically overwrite
```

Record:

```text
factory_type_bgmea
factory_type_mib
factory_type_final
factory_type_conflict
```

The final value should normally follow BGMEA unless the user explicitly asks for MiB precedence.

---

# 24. Missing Data Strategy

For every missing field:

```text
blank
```

not:

```text
Unknown
N/A
0
-
```

The audit file should explain why.

Example:

```json
{
    "factory_name": "Example Ltd.",
    "employee_male": null,
    "employee_female": null,
    "missing_fields": [
        "employee_male",
        "employee_female"
    ]
}
```

---

# 25. HTTP Request Strategy

Implement:

```python
requests.Session()
```

with:

- realistic User-Agent
- timeout
- retry
- exponential backoff
- rate limiting
- connection reuse

Example:

```python
TIMEOUT = 30
MAX_RETRIES = 5
REQUEST_DELAY = 1.0
```

Do not send hundreds of simultaneous requests.

Default to sequential or low-concurrency requests.

---

# 26. Retry Policy

Retry:

```text
429
500
502
503
504
connection timeout
temporary DNS failure
```

Do not endlessly retry:

```text
400
401
403
404
```

unless the site behavior indicates a temporary protection mechanism.

Use exponential backoff:

```text
1 sec
2 sec
4 sec
8 sec
16 sec
```

with jitter.

---

# 27. Robots / Terms / Access Controls

Before large-scale crawling:

1. Check `robots.txt`.
2. Check the site's terms/use restrictions.
3. Prefer publicly exposed structured data/API endpoints.
4. Do not bypass authentication, CAPTCHA, rate limits or access controls.
5. Do not attempt to evade anti-bot systems.
6. Respect reasonable request rates.

If the website explicitly prohibits automated collection, stop and report the restriction rather than bypassing it.

---

# 28. Caching

Every successful source response should be cached.

Recommended structure:

```text
cache/
    bgmea/
        page_001.html
        page_002.html
        ...
        factory_5161.html

    mib/
        factory_xxx.html
        factory_yyy.html
```

Use a metadata database:

```text
cache/index.sqlite
```

Suggested fields:

```text
url
source
http_status
retrieved_at
content_hash
local_path
```

This prevents repeated downloads.

---

# 29. Resume Capability

The scraper must be restartable.

Create:

```text
state/
    progress.json
```

Example:

```json
{
    "bgmea_pages_completed": 32,
    "bgmea_factories_completed": 850,
    "mib_records_completed": 3200
}
```

If the process crashes:

```bash
python run_pipeline.py
```

must continue from the last successful checkpoint.

---

# 30. Incremental Processing

Do not scrape everything again when only a small number of records changed.

Maintain:

```text
last_seen
last_scraped
content_hash
```

For each record.

If content hash has not changed:

```text
skip detailed processing
```

unless:

```text
--force-refresh
```

is provided.

---

# 31. Suggested Project Structure

Create:

```text
bgmea_mib_scraper/
│
├── SKILL.md
├── README.md
├── requirements.txt
├── .env.example
│
├── input/
│   └── factories.xlsx
│
├── output/
│   ├── factories_completed.xlsx
│   ├── validation_report.xlsx
│   └── unmatched_factories.xlsx
│
├── cache/
│   ├── bgmea/
│   └── mib/
│
├── state/
│   └── progress.json
│
├── logs/
│   └── scraper.log
│
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── http_client.py
│   ├── bgmea.py
│   ├── mib.py
│   ├── parser.py
│   ├── normalizer.py
│   ├── matcher.py
│   ├── validator.py
│   ├── excel_writer.py
│   └── pipeline.py
│
└── run_pipeline.py
```

---

# 32. Dependencies

Use:

```text
requests
beautifulsoup4
lxml
pandas
openpyxl
rapidfuzz
tenacity
python-dotenv
```

Optional:

```text
playwright
```

Only use Playwright when the required information cannot reasonably be obtained from static HTML or a publicly accessible structured endpoint.

Do not use browser automation by default.

---

# 33. Excel Processing

Use:

```python
openpyxl
```

for workbook preservation.

Use pandas only for intermediate tabular processing where appropriate.

Never assume the first worksheet is the target worksheet.

Inspect workbook sheets first.

Example:

```python
from openpyxl import load_workbook

wb = load_workbook(input_file)

print(wb.sheetnames)

for ws in wb.worksheets:
    print(ws.title, ws.max_row, ws.max_column)
```

---

# 34. Column Detection

Support slight variations in column names.

Example aliases:

```python
COLUMN_ALIASES = {
    "factory_name": [
        "Name of factory",
        "Factory Name",
        "Factory",
        "Name"
    ],

    "bgmea_registration_no": [
        "BGMEA registration no.",
        "BGMEA Reg No",
        "BGMEA Registration No",
        "Registration No"
    ],

    "factory_address": [
        "Address of factory",
        "Factory Address",
        "Address"
    ],

    "factory_type": [
        "Factory type (woven, knit, both)",
        "Factory Type",
        "Type"
    ],

    "management": [
        "management",
        "Management"
    ],

    "employee_male": [
        "Employee_male",
        "Employee Male",
        "Male Employee",
        "Male Workers"
    ],

    "employee_female": [
        "Employee_female",
        "Employee Female",
        "Female Employee",
        "Female Workers"
    ],

    "number_of_machines": [
        "No. of machines",
        "No. of Machines",
        "Number of machines",
        "Machines"
    ],

    "production_capacity": [
        "Production capacity",
        "Production Capacity",
        "Capacity"
    ]
}
```

---

# 35. Existing Excel Rows

If the workbook already contains factory names:

```text
use those records as the master list
```

Do not automatically append thousands of additional BGMEA records unless explicitly instructed.

For each existing row:

1. identify factory
2. search BGMEA
3. retrieve BGMEA record
4. search MiB
5. validate
6. populate missing fields

If the workbook is intended to contain the entire BGMEA member list, then build the master list from BGMEA.

---

# 36. Matching Existing Excel to BGMEA

For each Excel factory:

### First

Exact BGMEA registration number.

### Second

Normalized factory name.

### Third

Fuzzy name + address.

### Fourth

Manual-review queue.

Never overwrite an existing BGMEA registration number without evidence.

---

# 37. Manual Review Queue

Generate:

```text
output/manual_review.xlsx
```

with:

```text
Excel Factory Name
BGMEA Candidate
BGMEA Reg No
MiB Candidate
Name Score
Address Score
Overall Score
Reason
```

Example:

```text
ABC Garments Ltd
ABC Garments Ltd. Unit-2
1023
ABC Garments Limited
91
76
84
Possible unit mismatch
```

---

# 38. Validation Report

Generate:

```text
output/validation_report.xlsx
```

Sheets:

```text
Summary
Matched
Matched_With_Differences
BGMEA_Only
MiB_Only
Ambiguous
Duplicates
Missing_Data
Conflicts
```

---

# 39. Summary Statistics

The summary sheet should contain:

```text
Total Excel factories
Total BGMEA factories discovered
Total MiB factories discovered

Exact matches
Fuzzy matches
Ambiguous matches
BGMEA-only
MiB-only

Factory type conflicts
Address conflicts
Worker count conflicts
Duplicate candidates

Records with complete data
Records with missing data
```

---

# 40. Logging

Use Python logging.

Example:

```text
logs/scraper.log
```

Log:

```text
timestamp
level
source
URL
factory
action
result
error
```

Example:

```text
2026-09-10 20:00:31 INFO BGMEA page=14 records=20
2026-09-10 20:00:44 INFO Factory "ABC Garments Ltd." matched MiB score=96.2
2026-09-10 20:00:45 WARNING Factory "XYZ Ltd." ambiguous MiB candidates=3
```

Do not log passwords, tokens or credentials.

---

# 41. CLI

Implement:

```bash
python run_pipeline.py
```

Default behavior:

```text
detect input Excel
discover BGMEA pages
collect BGMEA
collect MiB
match
validate
populate Excel
generate reports
```

Support:

```bash
python run_pipeline.py --input input/factories.xlsx
```

```bash
python run_pipeline.py --output output/factories_completed.xlsx
```

```bash
python run_pipeline.py --limit 50
```

For testing only.

```bash
python run_pipeline.py --source bgmea
```

```bash
python run_pipeline.py --source mib
```

```bash
python run_pipeline.py --validate-only
```

```bash
python run_pipeline.py --resume
```

```bash
python run_pipeline.py --force-refresh
```

```bash
python run_pipeline.py --dry-run
```

---

# 42. Dry Run

Before making thousands of requests:

```bash
python run_pipeline.py --dry-run --limit 10
```

Dry run must show:

```text
Input workbook
Target worksheet
Detected columns
BGMEA starting URL
MiB starting URL
Number of Excel rows
Number of records to process
```

It should not modify the workbook.

---

# 43. Test Mode

Implement a small test set.

Example:

```bash
python run_pipeline.py --limit 10
```

Test:

```text
3A Fashions Ltd.
3S International Ltd.
4 You Clothing Ltd.
```

These examples are useful because the BGMEA and MiB sources both expose similarly named factories.

Verify:

```text
BGMEA registration number
name
type
address
worker data
machine data
capacity
```

before scaling up.

---

# 44. Data Quality Rules

Run validation before saving.

Rules:

### Registration number

Must be numeric/string numeric unless BGMEA explicitly provides another format.

### Male employees

Must be:

```text
integer >= 0
```

### Female employees

Must be:

```text
integer >= 0
```

### Machines

Must be:

```text
integer >= 0
```

### Factory type

Must be:

```text
woven
knit
both
blank
```

### Production capacity

Must not be empty if the source provides it.

---

# 45. Worker Consistency

If both values are available:

```python
total_workers = employee_male + employee_female
```

Compare with MiB's reported total.

Do not modify source values just because totals differ.

Instead:

```text
worker_count_conflict = TRUE
```

when the discrepancy exceeds a configurable threshold.

Example:

```python
difference_ratio = abs(bgmea_total - mib_total) / mib_total
```

Default:

```text
10%
```

---

# 46. Conflict Handling

Example:

BGMEA:

```text
Male = 1000
Female = 2000
```

MiB:

```text
Male = 900
Female = 2200
```

Output:

```text
Employee_male = 1000
Employee_female = 2000
```

because BGMEA is primary.

Audit:

```text
worker_count_conflict = TRUE
```

and preserve MiB values in the validation report.

---

# 47. Source Traceability

Every populated field should internally retain:

```text
source
source_url
retrieved_at
```

Example:

```json
{
    "employee_male": {
        "value": 1250,
        "source": "MiB",
        "url": "...",
        "retrieved_at": "2026-09-10T..."
    }
}
```

This allows later auditing.

Do not necessarily place these metadata columns in the user's final workbook.

Keep them in:

```text
validation_report.xlsx
```

or an internal JSON/SQLite database.

---

# 48. Database for Large Jobs

For thousands of records, use SQLite.

Database:

```text
state/factories.sqlite
```

Tables:

```text
bgmea_factories
mib_factories
matches
validation
requests
```

This is preferable to storing all progress in one JSON file.

---

# 49. Recommended Database Schema

```sql
CREATE TABLE bgmea_factories (
    id INTEGER PRIMARY KEY,
    registration_no TEXT,
    factory_name TEXT,
    address TEXT,
    factory_type TEXT,
    management TEXT,
    machines INTEGER,
    production_capacity TEXT,
    source_url TEXT,
    retrieved_at TEXT,
    content_hash TEXT
);
```

```sql
CREATE TABLE mib_factories (
    id INTEGER PRIMARY KEY,
    factory_name TEXT,
    address TEXT,
    factory_type TEXT,
    employee_male INTEGER,
    employee_female INTEGER,
    source_url TEXT,
    retrieved_at TEXT,
    content_hash TEXT
);
```

```sql
CREATE TABLE matches (
    id INTEGER PRIMARY KEY,
    bgmea_id INTEGER,
    mib_id INTEGER,
    name_score REAL,
    address_score REAL,
    type_score REAL,
    overall_score REAL,
    status TEXT
);
```

---

# 50. Architecture

Use this pipeline:

```text
Excel
  |
  v
Input Parser
  |
  v
BGMEA Discovery
  |
  v
BGMEA Detail Collection
  |
  v
Normalization
  |
  v
MiB Discovery
  |
  v
MiB Detail Collection
  |
  v
Entity Matching
  |
  v
Validation
  |
  +---------> Manual Review
  |
  v
Data Quality Checks
  |
  v
Excel Writer
  |
  +---------> Validation Report
  |
  +---------> Audit Log
```

---

# 51. Important Implementation Principle

Separate:

```text
collection
normalization
matching
validation
export
```

Do not put everything into one scraper function.

Bad:

```python
scrape_and_match_and_write_excel()
```

Preferred:

```python
collect_bgmea()
collect_mib()
normalize_records()
match_records()
validate_records()
write_excel()
write_validation_report()
```

---

# 52. Dynamic Website Changes

If a selector stops working:

1. Save the failing HTML.
2. Inspect the page.
3. identify the changed selector.
4. update the parser.
5. add a regression test.

Do not silently return blank data.

A parser failure should generate:

```text
PARSER_ERROR
```

in the logs.

---

# 53. CAPTCHA / Anti-Bot

If a CAPTCHA or human verification appears:

```text
STOP automated requests to that endpoint.
```

Do not:

- bypass CAPTCHA
- solve CAPTCHA automatically
- rotate IPs to evade blocking
- evade rate limits
- use unauthorized scraping methods

Report:

```text
Automation blocked by site protection.
Manual intervention or an official data-access mechanism is required.
```

---

# 54. MiB Usage Restrictions

MiB's website states that its data are collected and verified through its methodology and also includes restrictions concerning copying/reproduction of site materials.

Therefore, before running a large-scale automated extraction:

```text
verify the current MiB terms / permitted data access
```

and prefer official download/API mechanisms if provided.

Do not bypass technical restrictions.

Use MiB primarily for permitted validation/enrichment.

---

# 55. Provenance

For each final record, retain:

```text
BGMEA source URL
MiB source URL
retrieval date
match score
validation status
```

This is especially important because factory information can change over time.

---

# 56. Final Output

The main output must be:

```text
output/factories_completed.xlsx
```

with exactly the requested business columns:

```text
Name of factory
BGMEA registration no.
Address of factory
Factory type (woven, knit, both)
management
Employee_male
Employee_female
No. of machines
Production capacity
```

Additional validation information should go into separate sheets/files unless the user explicitly requests additional columns.

---

# 57. Expected Final Report

At completion print:

```text
========================================
BGMEA + MiB DATA COLLECTION COMPLETED
========================================

Input:
    factories.xlsx

Output:
    factories_completed.xlsx

Records:
    Excel records:              500
    BGMEA records discovered:   4290
    MiB records discovered:     3320

Matching:
    Exact matches:              410
    Fuzzy matches:               55
    Ambiguous:                   20
    BGMEA only:                  15

Validation:
    Fully validated:            390
    Conflicts:                   75
    Missing data:                35
    Duplicate candidates:        8

Manual review:
    output/manual_review.xlsx

Validation report:
    output/validation_report.xlsx
========================================
```

The numbers above are examples only. Always calculate actual values dynamically.

---

# 58. Claude Code Execution Instructions

When Claude Code receives this skill:

### Step 1

Inspect the workspace.

```bash
ls -la
find . -maxdepth 2 -type f
```

Locate the Excel input.

### Step 2

Inspect the workbook.

Determine:

```text
sheet
columns
row count
existing factory names
```

### Step 3

Inspect BGMEA.

Test:

```text
member-list
pagination
member details
```

### Step 4

Inspect MiB.

Determine whether:

```text
static HTML
JSON
API
embedded data
```

is available.

Prefer structured data.

### Step 5

Implement a 5–10 factory prototype.

Do not immediately scrape thousands of records.

### Step 6

Validate prototype manually.

Check:

```text
name
registration number
address
type
workers
machines
capacity
```

### Step 7

Run full collection with:

```text
cache
rate limiting
retry
checkpoint
SQLite state
logging
```

### Step 8

Run matching.

### Step 9

Run validation.

### Step 10

Write the final Excel.

### Step 11

Generate:

```text
validation_report.xlsx
manual_review.xlsx
```

### Step 12

Print the final summary.

---

# 59. Acceptance Criteria

The implementation is considered successful only when:

- [ ] Input Excel is preserved.
- [ ] Existing sheets are not accidentally deleted.
- [ ] BGMEA pagination is discovered dynamically.
- [ ] BGMEA registration numbers are collected.
- [ ] BGMEA detail pages are parsed.
- [ ] MiB records are collected through permitted access.
- [ ] Factory names are normalized.
- [ ] Units are distinguished.
- [ ] Fuzzy matching is implemented.
- [ ] Matching confidence is calculated.
- [ ] Conflicts are detected.
- [ ] Missing values are not invented.
- [ ] Duplicate candidates are detected.
- [ ] Requests are rate-limited.
- [ ] Failed requests are retried appropriately.
- [ ] Results are cached.
- [ ] Scraping can resume after interruption.
- [ ] Full logs are generated.
- [ ] Final Excel is generated.
- [ ] Validation report is generated.
- [ ] Manual-review file is generated.
- [ ] Source URLs are preserved internally.
- [ ] No CAPTCHA or access-control bypass is attempted.

---

# 60. Preferred Command Sequence

After implementation:

```bash
python run_pipeline.py --dry-run --limit 10
```

Then:

```bash
python run_pipeline.py --limit 10
```

After verifying the output:

```bash
python run_pipeline.py --resume
```

For a complete refresh:

```bash
python run_pipeline.py --force-refresh
```

---

# 61. Final Principle

The goal is not merely to scrape webpages.

The goal is to produce a **traceable, validated RMG factory dataset** where:

```text
BGMEA = primary membership/source dataset
MiB   = independent validation/enrichment dataset
Excel = final business deliverable
SQLite = processing state
Audit = provenance + conflicts
Manual review = uncertain matches
```

Every important value must be traceable back to a source.

Never silently guess.
Never silently merge factories.
Never silently overwrite conflicting information.
Never bypass access controls.
Always preserve the original input workbook.
Always make the pipeline resumable.