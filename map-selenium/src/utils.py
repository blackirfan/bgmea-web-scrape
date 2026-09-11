import re
import logging
from datetime import datetime

from config.settings import LOG_FILE


# ============================================================
# LOGGING
# ============================================================

def setup_logging():

    logging.basicConfig(

        level=logging.INFO,

        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),

        handlers=[

            logging.FileHandler(
                LOG_FILE,
                encoding="utf-8"
            ),

            logging.StreamHandler()
        ]
    )


# ============================================================
# TEXT
# ============================================================

def clean_text(text):

    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(text)
    ).strip()


def get_lines(text):

    return [
        clean_text(line)

        for line in text.splitlines()

        if clean_text(line)
    ]


# ============================================================
# FIELD EXTRACTION
# ============================================================

def after_label(
    lines,
    label
):

    label = label.lower().strip()

    for i, line in enumerate(lines):

        if line.lower().strip() == label:

            if i + 1 < len(lines):

                return lines[i + 1]

    return ""


def contains_line(
    lines,
    keyword
):

    keyword = keyword.lower()

    for line in lines:

        if keyword in line.lower():

            return line

    return ""


# ============================================================
# NUMBERS
# ============================================================

def extract_number(text):

    if not text:

        return None

    match = re.search(
        r"[\d,]+",
        str(text)
    )

    if not match:

        return None

    return int(
        match.group().replace(",", "")
    )


# ============================================================
# FACTORY ID
# ============================================================

def factory_id_from_url(url):

    return (
        url.rstrip("/")
        .split("/")
        [-1]
    )


# ============================================================
# TIME
# ============================================================

def current_timestamp():

    return datetime.now().isoformat()