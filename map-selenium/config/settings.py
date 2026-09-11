from pathlib import Path


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ============================================================
# WEBSITE
# ============================================================

BASE_URL = "https://mappedinbangladesh.org"

FACTORY_DIRECTORY_URL = (
    f"{BASE_URL}/site-map"
)

API_FACTORY_URL = (
    f"{BASE_URL}/api/factories"
)


# ============================================================
# DATA DIRECTORIES
# ============================================================

DATA_DIR = PROJECT_ROOT / "data"

RAW_DIR = (
    DATA_DIR /
    "raw" /
    "pages"
)

PROCESSED_DIR = (
    DATA_DIR /
    "processed"
)

CHECKPOINT_DIR = (
    DATA_DIR /
    "checkpoints"
)

URL_DIR = (
    DATA_DIR /
    "urls"
)


# ============================================================
# FILES
# ============================================================

FACTORY_URL_FILE = (
    URL_DIR /
    "factory_urls.csv"
)

RESULT_FILE = (
    PROCESSED_DIR /
    "mib_factories.csv"
)

EXCEL_FILE = (
    PROCESSED_DIR /
    "mib_factories.xlsx"
)

COMPLETED_FILE = (
    CHECKPOINT_DIR /
    "completed.csv"
)

LATLONG_FILE = (
    CHECKPOINT_DIR /
    "factory_latlong.csv"
)


# ============================================================
# LOGGING
# ============================================================

LOG_DIR = PROJECT_ROOT / "logs"

LOG_FILE = (
    LOG_DIR /
    "scraper.log"
)


# ============================================================
# SCRAPER SETTINGS
# ============================================================

EXPECTED_FACTORIES = 3320

PAGE_TIMEOUT = 90

WAIT_AFTER_PAGE = 1.5

MIN_DELAY = 0.8

MAX_DELAY = 1.5

SAVE_EVERY = 25

HEADLESS = True


# ============================================================
# LAT/LONG API SETTINGS
# ============================================================

API_MIN_DELAY = 0.3

API_MAX_DELAY = 0.7

API_TIMEOUT = 20

API_RETRIES = 3


# ============================================================
# CREATE DIRECTORIES
# ============================================================

for directory in [
    RAW_DIR,
    PROCESSED_DIR,
    CHECKPOINT_DIR,
    URL_DIR,
    LOG_DIR
]:

    directory.mkdir(
        parents=True,
        exist_ok=True
    )