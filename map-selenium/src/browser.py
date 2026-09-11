from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from config.settings import (
    PAGE_TIMEOUT,
    HEADLESS
)


def create_driver():

    options = Options()

    if HEADLESS:

        options.add_argument(
            "--headless=new"
        )

    options.add_argument(
        "--window-size=1920,1080"
    )

    options.add_argument(
        "--disable-gpu"
    )

    options.add_argument(
        "--disable-dev-shm-usage"
    )

    options.add_argument(
        "--no-sandbox"
    )

    options.add_argument(
        "--lang=en-US"
    )

    options.add_argument(
        "--disable-blink-features="
        "AutomationControlled"
    )

    driver = webdriver.Chrome(
        options=options
    )

    driver.set_page_load_timeout(
        PAGE_TIMEOUT
    )

    return driver