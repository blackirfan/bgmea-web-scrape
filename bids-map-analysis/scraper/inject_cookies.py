"""
Copy the mappedinbangladesh.org login session from the user's normal Chrome
profile into the already-running automation Chrome (attached via
--remote-debugging-port=9222), so the user doesn't have to log in twice.
"""
import sys
import time
import browser_cookie3
from selenium import webdriver

DEBUG_ADDRESS = "127.0.0.1:9222"
DOMAIN = "mappedinbangladesh.org"


def main():
    print(f"Reading cookies for {DOMAIN} from your default Chrome profile...")
    try:
        cj = browser_cookie3.chrome(domain_name=DOMAIN)
    except Exception as e:
        print(f"Failed to read cookies from Chrome's cookie store: {e}")
        sys.exit(1)

    cookies = list(cj)
    print(f"Found {len(cookies)} cookies for {DOMAIN}.")
    if not cookies:
        print("No cookies found — are you logged in, in your normal Chrome, at that domain?")
        sys.exit(1)

    options = webdriver.ChromeOptions()
    options.debugger_address = DEBUG_ADDRESS
    driver = webdriver.Chrome(options=options)

    driver.get(f"https://{DOMAIN}")
    time.sleep(1)

    ok, failed = 0, 0
    for c in cookies:
        cookie_dict = {
            "name": c.name,
            "value": c.value,
            "domain": c.domain,
            "path": c.path or "/",
        }
        if c.expires:
            cookie_dict["expiry"] = int(c.expires)
        try:
            driver.add_cookie(cookie_dict)
            ok += 1
        except Exception as e:
            failed += 1
            print(f"  skip {c.name}: {e}")

    print(f"Injected {ok} cookies ({failed} failed).")

    driver.get(f"https://{DOMAIN}/factories/10002")
    time.sleep(2)
    print("Reloaded factory page. Title:", driver.title)
    print("Current URL:", driver.current_url)


if __name__ == "__main__":
    main()
