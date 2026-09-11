import pandas as pd

from config.settings import (
    RESULT_FILE,
    EXCEL_FILE,
    COMPLETED_FILE
)


def load_completed_ids():

    if not RESULT_FILE.exists():

        return set()

    df = pd.read_csv(
        RESULT_FILE,
        dtype=str
    )

    if "factory_id" not in df.columns:

        return set()

    return set(
        df[
            "factory_id"
        ]
        .dropna()
        .astype(str)
    )


def save_factory(
    data
):

    exists = RESULT_FILE.exists()

    df = pd.DataFrame(
        [data]
    )

    df.to_csv(
        RESULT_FILE,
        mode="a",
        header=not exists,
        index=False,
        encoding="utf-8-sig"
    )


def finalize_dataset():

    if not RESULT_FILE.exists():

        return

    df = pd.read_csv(
        RESULT_FILE
    )

    # Remove duplicates
    df = df.drop_duplicates(
        subset=[
            "factory_id"
        ],
        keep="last"
    )

    # Save CSV
    df.to_csv(
        RESULT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    # Save Excel
    df.to_excel(
        EXCEL_FILE,
        index=False
    )

    return df