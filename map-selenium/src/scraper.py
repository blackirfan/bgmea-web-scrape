import logging
import random
import time

from tqdm import tqdm

from config.settings import (
    RAW_DIR,
    MIN_DELAY,
    MAX_DELAY,
    SAVE_EVERY
)

from src.utils import (
    factory_id_from_url
)

from src.parser import (
    parse_factory_page
)

from src.storage import (
    save_factory
)


logger = logging.getLogger(__name__)


def scrape_factories(
    driver,
    factory_urls,
    completed_ids
):

    total = len(
        factory_urls
    )

    remaining = [

        url

        for url in factory_urls

        if factory_id_from_url(url)
        not in completed_ids
    ]

    logger.info(
        "======================================"
    )

    logger.info(
        "TOTAL FACTORIES: %s",
        total
    )

    logger.info(
        "ALREADY COMPLETED: %s",
        len(completed_ids)
    )

    logger.info(
        "REMAINING: %s",
        len(remaining)
    )

    logger.info(
        "======================================"
    )

    success = 0

    failed = 0

    progress = tqdm(
        remaining,
        desc="Scraping factories",
        unit="factory"
    )

    for index, url in enumerate(
        progress,
        start=1
    ):

        factory_id = (
            factory_id_from_url(
                url
            )
        )

        progress.set_postfix(
            {
                "ID":
                    factory_id,

                "done":
                    len(completed_ids) +
                    success,

                "remaining":
                    len(remaining) -
                    index + 1
            }
        )

        try:

            logger.info(
                "Opening factory: %s",
                factory_id
            )

            driver.get(
                url
            )

            time.sleep(
                random.uniform(
                    MIN_DELAY,
                    MAX_DELAY
                )
            )

            # ---------------------------------------------
            # Parse
            # ---------------------------------------------

            data = parse_factory_page(
                driver,
                factory_id,
                url
            )

            # ---------------------------------------------
            # Save raw page
            # ---------------------------------------------

            raw_file = (
                RAW_DIR /
                f"{factory_id}.txt"
            )

            raw_file.write_text(
                data["raw_text"],
                encoding="utf-8"
            )

            # ---------------------------------------------
            # Save structured data
            # ---------------------------------------------

            save_factory(
                data
            )

            success += 1

            logger.info(
                "SUCCESS | %s | %s",
                factory_id,
                data["factory_name"]
            )

        except Exception as e:

            failed += 1

            logger.exception(
                "FAILED | %s | %s",
                factory_id,
                e
            )

        # ---------------------------------------------
        # Progress information
        # ---------------------------------------------

        if index % SAVE_EVERY == 0:

            logger.info(
                "CHECKPOINT | "
                "Processed: %s | "
                "Success: %s | "
                "Failed: %s | "
                "Remaining: %s",

                index,

                success,

                failed,

                len(remaining) - index
            )

    logger.info(
        "======================================"
    )

    logger.info(
        "SCRAPING SESSION FINISHED"
    )

    logger.info(
        "Success: %s",
        success
    )

    logger.info(
        "Failed: %s",
        failed
    )

    logger.info(
        "Remaining: %s",
        len(remaining) -
        success -
        failed
    )

    logger.info(
        "======================================"
    )