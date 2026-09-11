import argparse
import logging
import random
import time

import pandas as pd
from tqdm import tqdm

from config.settings import (
    API_MAX_DELAY,
    API_MIN_DELAY,
    EXCEL_FILE,
    FACTORY_URL_FILE,
    RESULT_FILE
)

from src.geocode import (
    fetch_factory_json_with_retries,
    load_done_ids,
    load_latlong_checkpoint,
    parse_latlong,
    save_latlong_row
)

from src.utils import (
    factory_id_from_url,
    setup_logging
)


logger = logging.getLogger(__name__)


# ============================================================
# STEP 1: FETCH LAT/LONG FOR EVERY KNOWN FACTORY ID
# ============================================================

def fetch_all_latlong(limit=None):

    urls = (
        pd.read_csv(FACTORY_URL_FILE)
        ["factory_url"]
        .dropna()
        .drop_duplicates()
        .tolist()
    )

    factory_ids = [
        factory_id_from_url(url)
        for url in urls
    ]

    done_ids = load_done_ids()

    remaining = [
        fid
        for fid in factory_ids
        if fid not in done_ids
    ]

    if limit:

        remaining = remaining[:limit]

    logger.info(
        "======================================"
    )

    logger.info(
        "TOTAL FACTORIES: %s",
        len(factory_ids)
    )

    logger.info(
        "ALREADY FETCHED: %s",
        len(done_ids)
    )

    logger.info(
        "REMAINING (this run): %s",
        len(remaining)
    )

    logger.info(
        "======================================"
    )

    success = 0

    failed = 0

    progress = tqdm(
        remaining,
        desc="Fetching lat/long",
        unit="factory"
    )

    for factory_id in progress:

        progress.set_postfix(
            {
                "ID": factory_id,
                "ok": success,
                "failed": failed
            }
        )

        try:

            payload = (
                fetch_factory_json_with_retries(
                    factory_id
                )
            )

            record = parse_latlong(
                payload,
                factory_id
            )

            save_latlong_row(
                record
            )

            success += 1

            logger.info(
                "SUCCESS | %s | lat=%s lon=%s",
                factory_id,
                record["latitude"],
                record["longitude"]
            )

        except Exception as e:

            failed += 1

            logger.exception(
                "FAILED | %s | %s",
                factory_id,
                e
            )

        time.sleep(
            random.uniform(
                API_MIN_DELAY,
                API_MAX_DELAY
            )
        )

    logger.info(
        "======================================"
    )

    logger.info(
        "LAT/LONG FETCH FINISHED"
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
        "======================================"
    )


# ============================================================
# STEP 2: MERGE LAT/LONG INTO THE MIB DATASET
# ============================================================

def merge_into_mib_dataset():

    if not RESULT_FILE.exists():

        logger.warning(
            "%s does not exist yet - run the main scraper first.",
            RESULT_FILE
        )

        return None

    latlong = load_latlong_checkpoint()

    latlong["factory_id"] = (
        latlong["factory_id"]
        .astype(str)
    )

    df = pd.read_csv(
        RESULT_FILE,
        dtype={
            "factory_id": str
        }
    )

    # Drop any previous merge so re-running this step is safe.
    drop_cols = [
        col
        for col in [
            "latitude",
            "longitude",
            "police_station_name"
        ]
        if col in df.columns
    ]

    if drop_cols:

        df = df.drop(
            columns=drop_cols
        )

    df = df.merge(
        latlong,
        on="factory_id",
        how="left"
    )

    df.to_csv(
        RESULT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    df.to_excel(
        EXCEL_FILE,
        index=False
    )

    matched = (
        df["latitude"]
        .notna()
        .sum()
    )

    logger.info(
        "Merged lat/long into %s",
        RESULT_FILE
    )

    logger.info(
        "Matched: %s / %s factories",
        matched,
        len(df)
    )

    return df


# ============================================================
# MAIN
# ============================================================

def main():

    setup_logging()

    parser = argparse.ArgumentParser(
        description=(
            "Fetch latitude/longitude for every MiB factory via the "
            "public MiB API and merge it into mib_factories.csv/.xlsx"
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only fetch this many new factories (for testing)."
    )

    parser.add_argument(
        "--merge-only",
        action="store_true",
        help=(
            "Skip fetching; just re-merge the existing lat/long "
            "checkpoint into the MiB dataset."
        )
    )

    args = parser.parse_args()

    logger.info(
        "=========================================="
    )

    logger.info(
        "MAPPED IN BANGLADESH - LAT/LONG FETCHER"
    )

    logger.info(
        "=========================================="
    )

    if not args.merge_only:

        fetch_all_latlong(
            limit=args.limit
        )

    merge_into_mib_dataset()

    logger.info(
        "DONE."
    )


if __name__ == "__main__":

    main()
