"""Offline tests for field extraction and normalisation.

    python -m unittest test_fields -v

The HTML-parsing tests reuse the Details pages cached by the sibling
requests-based project if it is present; otherwise they skip.
"""

import unittest
from pathlib import Path

import fields

CACHE = Path(__file__).resolve().parent.parent / "bgmea_mib_scraper" / "cache" / "bgmea"


def page(member):
    p = CACHE / f"factory_{member}.html"
    if not p.exists():
        raise unittest.SkipTest(f"{p} not available")
    return p.read_text(encoding="utf-8", errors="replace")


class TestNormalise(unittest.TestCase):
    def test_clean_int(self):
        self.assertEqual(fields.clean_int("1,250"), 1250)
        self.assertEqual(fields.clean_int("2,858 workers"), 2858)
        self.assertIsNone(fields.clean_int("0"))
        self.assertIsNone(fields.clean_int(""))
        self.assertIsNone(fields.clean_int(None))

    def test_registration_stays_string(self):
        self.assertEqual(fields.clean_registration("5161.0"), "5161")
        self.assertEqual(fields.clean_registration("60"), "60")
        self.assertIsNone(fields.clean_registration("0"))

    def test_type_mapping(self):
        self.assertEqual(fields.normalise_type(["Woven", "Knit"])[0], "both")
        self.assertEqual(fields.normalise_type(["Knitwear"])[0], "knit")
        self.assertEqual(fields.normalise_type(["Woven"])[0], "woven")

    def test_type_not_guessed(self):
        self.assertIsNone(fields.normalise_type(["Sweater"])[0])
        self.assertIsNone(fields.normalise_type(["Composite"])[0])
        self.assertIsNone(fields.normalise_type([])[0])

    def test_clean_date(self):
        self.assertEqual(fields.clean_date("2026-01-21"), "2026-01-21")
        self.assertIsNone(fields.clean_date("0"))
        self.assertIsNone(fields.clean_date(""))
        self.assertIsNone(fields.clean_date(None))

    def test_capacity_keeps_unit(self):
        self.assertEqual(
            fields.normalise_capacity("600000", "production capacity (yearly in dozen)"),
            "600000 dozen/year")
        self.assertEqual(fields.normalise_capacity("500,000 pcs/month", ""),
                         "500,000 pcs/month")
        self.assertIsNone(fields.normalise_capacity("0", ""))


class TestExtract(unittest.TestCase):
    def test_3a_fashions(self):
        rec, _ = fields.extract(page(2))
        self.assertEqual(rec["Name of factory"], "3A Fashions Ltd.")
        self.assertEqual(rec["BGMEA registration no."], "5161")
        self.assertEqual(rec["Factory type (woven, knit, both)"], "knit")
        self.assertEqual(rec["management"], "350")
        self.assertIsNone(rec["Employee_male"])
        self.assertEqual(rec["No. of machines"], 114)
        self.assertEqual(rec["Production capacity"], "600000 dozen/year")
        self.assertIn("Khejur", rec["Address of factory"])

    def test_factory_address_preferred_over_mailing(self):
        rec, _ = fields.extract(page(7))
        self.assertIn("Senpara Parbata", rec["Address of factory"])
        self.assertNotIn("Gulshan", rec["Address of factory"])

    def test_woven_and_knit_is_both(self):
        rec, _ = fields.extract(page(5276))
        self.assertEqual(rec["Factory type (woven, knit, both)"], "both")
        self.assertEqual(rec["Employee_male"], 90)
        self.assertEqual(rec["Employee_female"], 100)

    def test_address_has_no_contact_noise(self):
        rec, _ = fields.extract(page(5))
        for noise in ("Phone", "@", "Fax"):
            self.assertNotIn(noise, rec["Address of factory"])


if __name__ == "__main__":
    unittest.main()
