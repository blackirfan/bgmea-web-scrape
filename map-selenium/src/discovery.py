import logging
import time

import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from config.settings import (
    FACTORY_DIRECTORY_URL,
    FACTORY_URL_FILE
)


logger = logging.getLogger(__name__)


def discover_factory_urls(driver):

    logger.info(
        "Opening MiB factory directory..."
    )

    driver.get(
        FACTORY_DIRECTORY_URL
    )

    WebDriverWait(
        driver,
        60
    ).until(

        lambda d:
        len(
            d.find_elements(
                By.CSS_SELECTOR,
                'a[href*="/factories/"]'
            )
        ) > 0
    )

    time.sleep(3)

    links = driver.find_elements(
        By.CSS_SELECTOR,
        'a[href*="/factories/"]'
    )

    urls = set()

    for link in links:

        try:

            href = link.get_attribute(
                "href"
            )

            if not href:
                continue

            if "/factories/" not in href:
                continue

            href = href.split("?")[0]

            urls.add(href)

        except Exception:

            continue

    urls = sorted(urls)

    logger.info(
        "Factory URLs discovered: %s",
        len(urls)
    )

    pd.DataFrame(
        {
            "factory_url": urls
        }
    ).to_csv(
        FACTORY_URL_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    return urls