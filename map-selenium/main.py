import logging
import pandas as pd

from src.browser import create_driver

from src.discovery import (
    discover_factory_urls
)

from src.storage import (
    load_completed_ids,
    finalize_dataset
)

from src.scraper import (
    scrape_factories
)

from src.utils import (
    setup_logging
)

from config.settings import (
    FACTORY_URL_FILE
)


def main():

    setup_logging()

    logger = logging.getLogger(
        __name__
    )

    logger.info(
        "=========================================="
    )

    logger.info(
        "MAPPED IN BANGLADESH SCRAPER"
    )

    logger.info(
        "=========================================="
    )

    driver = create_driver()

    try:

        # ====================================================
        # STEP 1
        # DISCOVER FACTORIES
        # ====================================================

        if FACTORY_URL_FILE.exists():

            logger.info(
                "Loading existing factory URLs..."
            )

            df = pd.read_csv(
                FACTORY_URL_FILE
            )

            factory_urls = (
                df["factory_url"]
                .dropna()
                .drop_duplicates()
                .tolist()
            )

        else:

            factory_urls = (
                discover_factory_urls(
                    driver
                )
            )

        logger.info(
            "Factory URLs: %s",
            len(factory_urls)
        )

        # ====================================================
        # STEP 2
        # CHECKPOINT
        # ====================================================

        completed_ids = (
            load_completed_ids()
        )

        # ====================================================
        # STEP 3
        # SCRAPE
        # ====================================================

        scrape_factories(
            driver,
            factory_urls,
            completed_ids
        )

        # ====================================================
        # STEP 4
        # FINALIZE
        # ====================================================

        df = finalize_dataset()

        if df is not None:

            logger.info(
                "Final dataset created."
            )

            logger.info(
                "Total records: %s",
                len(df)
            )

        logger.info(
            "SCRAPER FINISHED."
        )

    finally:

        driver.quit()


if __name__ == "__main__":

    main()