from src.utils import (
    after_label,
    contains_line,
    extract_number,
    clean_text
)


def parse_factory_page(
    driver,
    factory_id,
    url
):

    body = driver.find_element(
        "tag name",
        "body"
    ).text

    lines = [
        line.strip()

        for line in body.splitlines()

        if line.strip()
    ]

    # ========================================================
    # RESULT
    # ========================================================

    data = {

        "factory_id":
            factory_id,

        "factory_url":
            url,

        "factory_name":
            "",

        "last_updated":
            "",

        "factory_type":
            "",

        "establishment_year":
            "",

        "premises_type":
            "",

        "memberships":
            "",

        "building_safety_inspection":
            "",

        "workers":
            None,

        "sewing_lines":
            None,

        "sewing_machines":
            None,

        "products":
            "",

        "production_capacity":
            "",

        "buyers_brands_agents":
            "",

        "export_countries":
            "",

        "etp":
            "",

        "solar":
            "",

        "certifications":
            "",

        "worker_facilities":
            "",

        "workplace_committees":
            "",

        "address":
            "",

        "raw_text":
            body
    }

    # ========================================================
    # FACTORY NAME
    # ========================================================

    try:

        h1 = driver.find_elements(
            "tag name",
            "h1"
        )

        if h1:

            data["factory_name"] = (
                clean_text(
                    h1[0].text
                )
            )

    except Exception:

        pass

    if not data["factory_name"]:

        data["factory_name"] = clean_text(
            driver.title
        )

    # ========================================================
    # LAST UPDATED
    # ========================================================

    line = contains_line(
        lines,
        "Last Updated"
    )

    if line:

        data["last_updated"] = (
            line
            .split(":", 1)[-1]
            .strip()
        )

    # ========================================================
    # BASIC INFORMATION
    # ========================================================

    data["factory_type"] = after_label(
        lines,
        "Factory Type"
    )

    data["establishment_year"] = after_label(
        lines,
        "Establishment Year"
    )

    data["premises_type"] = after_label(
        lines,
        "Premises Type"
    )

    data["memberships"] = after_label(
        lines,
        "Memberships"
    )

    data[
        "building_safety_inspection"
    ] = after_label(
        lines,
        "Building Safety Inspection"
    )

    # ========================================================
    # WORKERS
    # ========================================================

    data["workers"] = extract_number(
        after_label(
            lines,
            "Workers"
        )
    )

    # ========================================================
    # PRODUCTION
    # ========================================================

    data["sewing_lines"] = extract_number(
        after_label(
            lines,
            "No. of Sewing Lines"
        )
    )

    data["sewing_machines"] = extract_number(
        after_label(
            lines,
            "No. of Sewing Machines"
        )
    )

    data["products"] = after_label(
        lines,
        "Products"
    )

    data["production_capacity"] = after_label(
        lines,
        "Production Capacity"
    )

    data[
        "buyers_brands_agents"
    ] = after_label(
        lines,
        "Brand / Buyer / Agent"
    )

    data["export_countries"] = after_label(
        lines,
        "Export Countries"
    )

    # ========================================================
    # ESG
    # ========================================================

    data["etp"] = after_label(
        lines,
        "ETP"
    )

    data["solar"] = after_label(
        lines,
        "Solar Panel Usage"
    )

    data["certifications"] = after_label(
        lines,
        "Certifications"
    )

    data["worker_facilities"] = after_label(
        lines,
        "Worker Facilities"
    )

    data[
        "workplace_committees"
    ] = after_label(
        lines,
        "Workplace Committees"
    )

    # ========================================================
    # ADDRESS
    # ========================================================

    data["address"] = after_label(
        lines,
        "Address"
    )

    return data