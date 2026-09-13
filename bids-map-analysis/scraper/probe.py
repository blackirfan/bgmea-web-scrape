"""
One-off probe: attach to an already-running, logged-in Chrome (started with
--remote-debugging-port=9222) and dump the DOM of one factory page so we can
design real selectors instead of guessing from screenshots.

Usage:
    py -3 scraper/probe.py https://mappedinbangladesh.org/factories/10002
"""
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By

DEBUG_ADDRESS = "127.0.0.1:9222"


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else "https://mappedinbangladesh.org/factories/10002"

    options = webdriver.ChromeOptions()
    options.debugger_address = DEBUG_ADDRESS
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    driver.implicitly_wait(5)

    print("Current URL after load:", driver.current_url)
    print("Title:", driver.title)

    with open("scraper/probe_page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Saved full page source -> scraper/probe_page_source.html")

    # Try to find tab-like clickable elements
    print("\n--- Elements containing 'General' / 'Production' / 'ESG' / 'Address' ---")
    for label in ["General", "Production", "ESG", "Address"]:
        try:
            els = driver.find_elements(By.XPATH, f"//*[normalize-space(text())='{label}']")
            for el in els:
                print(f"[{label}] tag={el.tag_name} class={el.get_attribute('class')!r} outerHTML_len={len(el.get_attribute('outerHTML') or '')}")
        except Exception as e:
            print(f"[{label}] error: {e}")


if __name__ == "__main__":
    main()
