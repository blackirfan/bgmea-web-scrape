# BGMEA member list — autonomous Selenium scraper

Opens the BGMEA general member list in headless Chrome, walks every page,
opens every factory's **Details** page, and writes the ten business columns to
an Excel file. One factory per row. Runs to completion on its own with no
arguments.

## Install

```bash
pip install -r requirements.txt
```

Google Chrome must be installed. Selenium 4 downloads the matching
`chromedriver` itself, so there is nothing to put on `PATH`.

## Run

```bash
python scrape_bgmea_selenium.py                 # full run, headless
python scrape_bgmea_selenium.py --show          # watch the browser
python scrape_bgmea_selenium.py --limit 25      # first 25 factories
python scrape_bgmea_selenium.py --pages 3       # first 3 list pages
python scrape_bgmea_selenium.py --template your_form.xlsx
python scrape_bgmea_selenium.py --restart       # discard saved progress
```

The full run is about 4,300 Details pages at roughly one per 1.5 seconds, so
allow around two to three hours. `--pause` changes the wait after each page
load (default 1.0 second); lower it only if the site stays responsive.

## Output (in `output/`)

| File | Contents |
|---|---|
| `bgmea_factories.xlsx` | the ten columns, one row per factory |
| `bgmea_factories_audit.xlsx` | for every factory, which fields are blank and why |
| `state.json` | resume checkpoint, written after each factory |

## Resumable

Progress is saved after every factory. Stop the run at any time — Ctrl-C, a
crash, a reboot — and start it again; it continues from the next unread
factory. The Excel files are rewritten in full at each checkpoint, so they are
always complete for whatever has been read so far. `--restart` throws the
checkpoint away and begins again.

## The ten columns and where they come from

All values come from the member's Details page. The tab panes (Company,
Address, Final) are all in the page HTML, so the scraper reads them without
clicking between tabs.

| Column | Source on the Details page |
|---|---|
| Name of factory | page title / header |
| BGMEA registration no. | Company tab, "BGMEA Reg. No." — kept as text, so `5161` never becomes `5161.0` |
| Address of factory | Address tab, "Factory Address" (the mailing address is used only if there is no factory address, and the two are never joined) |
| Date of Establishment | Final tab, "Date of Establishment" |
| Factory type (woven, knit, both) | Final tab, "Factory Type" table |
| management | Final tab, "No. of Employees" table, Management column (a headcount, not an ownership category) |
| Employee_male / Employee_female | Final tab, "No. of Employees" table |
| No. of machines | Final tab, "No of Machines" |
| Production capacity | Final tab, "Production Capacity", with its unit kept, e.g. `600000 dozen/year` |

## Rules

- A field the page does not provide is left **blank** — never `0`, `N/A` or a
  guess. Every blank has a reason in the audit file.
- A bare `0` in a numeric field is treated as "not reported", because the BGMEA
  form defaults empty number fields to 0.
- "Sweater" or "Composite" on their own do not become knit or woven; the type
  is left blank with a note.
- If the site ever shows a CAPTCHA or bot-challenge page, the scraper stops and
  says so instead of trying to get around it.

## Files

```
scrape_bgmea_selenium.py   the autonomous run: driver, member list, detail loop, resume
fields.py                  Details-page HTML -> the nine fields (pure, testable)
excel_out.py               fresh workbook, or filling an existing template
```
