#!/usr/bin/env python
"""Autonomous Selenium scraper for the BGMEA general member list.

What it does, with no arguments:

    1. opens https://www.bgmea.com.bd/page/member-list in headless Chrome
    2. reads the pagination control to learn the real page count
    3. walks every list page and records each member's Details link
    4. opens every Details page and reads the ten business fields
    5. writes output/bgmea_factories.xlsx  (one factory per row)
       and output/bgmea_factories_audit.xlsx  (why any field is blank)

It is resumable. Progress is saved to output/state.json after every member, so
stopping the run (Ctrl-C, a crash, a reboot) and starting it again continues
from the next unread factory. The Excel files are rewritten from scratch on
each checkpoint, so they are always complete for whatever has been read so far.

    python scrape_bgmea_selenium.py                 # full run, headless
    python scrape_bgmea_selenium.py --show          # watch the browser work
    python scrape_bgmea_selenium.py --limit 25      # first 25 members only
    python scrape_bgmea_selenium.py --pages 3       # first 3 list pages only
    python scrape_bgmea_selenium.py --template t.xlsx   # fill an existing sheet
    python scrape_bgmea_selenium.py --restart       # ignore saved progress

Selenium 4 downloads the matching chromedriver itself; no PATH setup needed.
Only Google Chrome must be installed.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

from selenium import webdriver
from selenium.common.exceptions import (NoSuchElementException,
                                        TimeoutException, WebDriverException)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import fields
from excel_out import OutputLocked, write_audit, write_template, write_workbook

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
STATE = OUT / "state.json"
MEMBER_LIST = "https://www.bgmea.com.bd/page/member-list"

CHALLENGE = ("captcha", "cf-challenge", "attention required", "are you a human",
             "checking your browser")


# --------------------------------------------------------------------------- #
#  driver                                                                     #
# --------------------------------------------------------------------------- #

def make_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,1000")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--log-level=3")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/152.0.0.0 Safari/537.36")
    opts.add_experimental_option("excludeSwitches", ["enable-automation",
                                                     "enable-logging"])
    opts.page_load_strategy = "eager"
    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(45)
    return driver


def get(driver, url, tries=4):
    """Load a URL with retry and backoff. Raise on a bot-challenge page."""
    last = None
    for attempt in range(tries):
        try:
            driver.get(url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "table")))
            html = driver.page_source
            low = html[:5000].lower()
            if any(marker in low for marker in CHALLENGE):
                raise RuntimeError(
                    "BGMEA served a bot-challenge page. Stopping rather than "
                    "trying to bypass it; retry later or use --show.")
            return html
        except TimeoutException as exc:
            last = exc
        except WebDriverException as exc:
            last = exc
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"could not load {url}: {last}")


# --------------------------------------------------------------------------- #
#  member list                                                                #
# --------------------------------------------------------------------------- #

def discover_last_page(driver):
    nums = set()
    for a in driver.find_elements(By.CSS_SELECTOR, "ul.pagination a[href]"):
        m = re.search(r"[?&]page=(\d+)", a.get_attribute("href") or "")
        if m:
            nums.add(int(m.group(1)))
    return max(nums) if nums else 1


def read_list_page(driver):
    rows = []
    for tr in driver.find_elements(By.CSS_SELECTOR, "table tbody tr"):
        cells = tr.find_elements(By.TAG_NAME, "td")
        if len(cells) < 2:
            continue
        try:
            link = tr.find_element(By.CSS_SELECTOR, "a[href*='/member/']")
            url = link.get_attribute("href")
        except NoSuchElementException:
            url = None
        mid = None
        if url:
            m = re.search(r"/member/(\d+)", url)
            mid = m.group(1) if m else None
        rows.append({
            "member_id": mid,
            "name": cells[0].text.strip(),
            "reg_no": cells[1].text.strip() if len(cells) > 1 else None,
            "url": url,
        })
    return rows


def collect_member_index(driver, max_pages=None, pause=1.0):
    print("Opening the BGMEA member list...")
    get(driver, MEMBER_LIST)
    last = discover_last_page(driver)
    if max_pages:
        last = min(last, max_pages)
    print(f"  pagination shows {last} page(s)")

    index, seen = [], set()
    for page in range(1, last + 1):
        if page > 1:
            get(driver, f"{MEMBER_LIST}?page={page}")
            time.sleep(pause)
        for row in read_list_page(driver):
            key = row["member_id"] or (row["name"], row["reg_no"])
            if key in seen:
                continue
            seen.add(key)
            index.append(row)
        print(f"  page {page}/{last}  members so far: {len(index)}", flush=True)
    return index


# --------------------------------------------------------------------------- #
#  detail page                                                                #
# --------------------------------------------------------------------------- #

def scrape_member(driver, member, pause=1.0):
    url = member["url"]
    if not url:
        return None, ["member row had no Details link"]
    get(driver, url)
    time.sleep(pause)
    record, notes = fields.extract(driver.page_source, url)
    if not record.get("Name of factory"):
        record["Name of factory"] = member.get("name")
    if not record.get("BGMEA registration no."):
        record["BGMEA registration no."] = fields.clean_registration(
            member.get("reg_no"))
    return record, notes


# --------------------------------------------------------------------------- #
#  state                                                                      #
# --------------------------------------------------------------------------- #

def load_state():
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {"index": [], "records": [], "audit": [], "done": []}


def save_state(state):
    OUT.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                     encoding="utf-8")


def flush_excel(state, template=None, final=False):
    """Rewrite the Excel outputs. A locked target never stops the run:
    state.json still holds everything and the data is written to a
    *.locked.xlsx alongside instead."""
    records = list(state["records"])
    xlsx = OUT / "bgmea_factories.xlsx"
    warnings = []
    try:
        if template:
            write_template(template, xlsx, records)
        else:
            write_workbook(xlsx, records)
    except OutputLocked as exc:
        warnings.append(str(exc))
    try:
        write_audit(OUT / "bgmea_factories_audit.xlsx", state["audit"])
    except OutputLocked as exc:
        warnings.append(str(exc))
    for w in warnings:
        print(f"  note: {w}")
    if final and warnings:
        # Guarantee the complete dataset exists under a free name.
        stamp = time.strftime("%Y%m%d_%H%M%S")
        safe = OUT / f"bgmea_factories_{stamp}.xlsx"
        write_workbook(safe, records)
        print(f"  final data also written to {safe.name}")


# --------------------------------------------------------------------------- #
#  main                                                                       #
# --------------------------------------------------------------------------- #

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, help="stop after N members")
    ap.add_argument("--pages", type=int, help="only read the first N list pages")
    ap.add_argument("--template", help="existing .xlsx to copy and fill")
    ap.add_argument("--show", action="store_true", help="show the browser")
    ap.add_argument("--restart", action="store_true", help="ignore saved state")
    ap.add_argument("--pause", type=float, default=1.0,
                    help="seconds to wait after each page load (default 1.0)")
    ap.add_argument("--flush-every", type=int, default=20,
                    help="rewrite the Excel files every N members")
    args = ap.parse_args(argv)

    OUT.mkdir(parents=True, exist_ok=True)
    if args.restart and STATE.exists():
        STATE.unlink()

    state = load_state()
    driver = make_driver(headless=not args.show)

    try:
        if not state["index"]:
            state["index"] = collect_member_index(driver, args.pages, args.pause)
            save_state(state)
        else:
            print(f"Resuming: {len(state['index'])} members indexed, "
                  f"{len(state['done'])} already read")

        members = state["index"]
        if args.limit:
            members = members[:args.limit]

        done = set(state["done"])
        started = time.monotonic()
        processed = 0

        for i, member in enumerate(members, 1):
            key = member["member_id"] or member["name"]
            if key in done:
                continue
            try:
                record, notes = scrape_member(driver, member, args.pause)
            except RuntimeError as exc:
                print(f"\n{exc}", file=sys.stderr)
                break
            except WebDriverException as exc:
                notes = [f"selenium error: {exc.__class__.__name__}"]
                record = None

            name = member["name"]
            remaining = len(members) - i
            if record is None:
                state["audit"].append([name, member.get("reg_no"),
                                       member.get("url"), "; ".join(notes)])
                print(f"  [{i}/{len(members)}] remaining={remaining}  "
                      f"{name}  SKIPPED: {notes[0]}", flush=True)
            else:
                state["records"].append(record)
                state["audit"].append([
                    record["Name of factory"], record["BGMEA registration no."],
                    member.get("url"),
                    "; ".join(notes) or "all ten fields populated"])
                print(f"  [{i}/{len(members)}] remaining={remaining}  {name}",
                      flush=True)

            done.add(key)
            state["done"] = sorted(done)
            processed += 1

            if processed % args.flush_every == 0:
                save_state(state)
                flush_excel(state, args.template)
                rate = processed / max(time.monotonic() - started, 1e-6)
                eta = remaining / rate / 60 if rate else 0
                print(f"  [{i}/{len(members)}]  remaining={remaining}  "
                      f"{rate*60:.0f}/min  ETA {eta:.0f} min", flush=True)

        save_state(state)
        flush_excel(state, args.template, final=True)

    finally:
        driver.quit()

    records = state["records"]
    complete = sum(1 for r in records
                   if all(r.get(c) not in (None, "") for c in fields.BUSINESS_COLUMNS))
    print()
    print("=" * 46)
    print(f"  Members indexed     : {len(state['index'])}")
    print(f"  Factories written   : {len(records)}")
    print(f"  All ten fields      : {complete}")
    print(f"  Some fields blank   : {len(records) - complete}")
    print(f"  Output              : {OUT / 'bgmea_factories.xlsx'}")
    print(f"  Audit / reasons     : {OUT / 'bgmea_factories_audit.xlsx'}")
    print("=" * 46)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
