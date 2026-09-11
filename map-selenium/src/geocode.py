import json
import logging
import time
import urllib.error
import urllib.request

import pandas as pd

from config.settings import (
    API_FACTORY_URL,
    API_RETRIES,
    API_TIMEOUT,
    LATLONG_FILE
)


logger = logging.getLogger(__name__)


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


LATLONG_COLUMNS = [
    "factory_id",
    "latitude",
    "longitude",
    "police_station_name"
]


# ============================================================
# API CALL
# ============================================================

def fetch_factory_json(
    factory_id,
    timeout=API_TIMEOUT
):

    url = f"{API_FACTORY_URL}/{factory_id}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout
    ) as response:

        return json.load(response)


def fetch_factory_json_with_retries(
    factory_id,
    retries=API_RETRIES
):

    last_error = None

    for attempt in range(1, retries + 1):

        try:

            return fetch_factory_json(
                factory_id
            )

        except Exception as e:

            last_error = e

            logger.warning(
                "RETRY %s/%s | %s | %s",
                attempt,
                retries,
                factory_id,
                e
            )

            time.sleep(
                attempt
            )

    raise last_error


# ============================================================
# PARSE
# ============================================================

def parse_latlong(
    payload,
    factory_id
):

    # NOTE: `latitude`, `longitude` and `police_station_name` are
    # top-level fields the MiB API serves unblurred even to
    # anonymous callers (see payload["blurrables"], which only ever
    # lists "brands", "address", "phone", "certifications"). Do not
    # pull anything from payload["address"] here - it is randomised
    # per request and not real data.

    return {
        "factory_id": str(factory_id),

        "latitude": payload.get("latitude"),

        "longitude": payload.get("longitude"),

        "police_station_name": payload.get(
            "police_station_name"
        )
    }


# ============================================================
# CHECKPOINT (id -> lat/long cache, resumable)
# ============================================================

def load_latlong_checkpoint():

    if not LATLONG_FILE.exists():

        return pd.DataFrame(
            columns=LATLONG_COLUMNS
        )

    df = pd.read_csv(
        LATLONG_FILE,
        dtype={
            "factory_id": str
        }
    )

    if "factory_id" not in df.columns:

        return pd.DataFrame(
            columns=LATLONG_COLUMNS
        )

    return df


def load_done_ids():

    df = load_latlong_checkpoint()

    return set(
        df["factory_id"]
        .dropna()
        .astype(str)
    )


def save_latlong_row(
    record
):

    exists = LATLONG_FILE.exists()

    pd.DataFrame(
        [record]
    ).to_csv(
        LATLONG_FILE,
        mode="a",
        header=not exists,
        index=False,
        encoding="utf-8-sig"
    )
