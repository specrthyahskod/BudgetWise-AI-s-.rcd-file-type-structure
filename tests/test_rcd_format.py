"""Verification tests for the BudgetWise .rcd archive format."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.rcd_format import InvalidRCDFileError, RCDFileManager


SAMPLE_TRANSACTIONS = [
    {
        "date": "2026-09-14",
        "category": "Groceries",
        "description": "Woolworths Broadway",
        "amount": 74.50,
    },
    {
        "date": "2026-09-15",
        "category": "Transport",
        "description": "Opal Transit Top-up",
        "amount": 25.00,
    },
    {
        "date": "2026-09-17",
        "category": "Dining",
        "description": "Uni Student Cafe",
        "amount": 16.80,
    },
    {
        "date": "2026-09-18",
        "category": "Utilities",
        "description": "Mobile Plan Bill",
        "amount": 62.30,
    },
]

SAMPLE_SUMMARY = {
    "total_expenses": 178.60,
    "record_count": 4,
    "daily_average": 29.77,
    "currency": "AUD",
}


class RCDFormatTests(unittest.TestCase):
    def test_pack_unpack_round_trip(self) -> None:
        packed = RCDFileManager.pack_weekly_data(
            username="riddhiman_test",
            week_start="2026-09-14",
            week_end="2026-09-20",
            transactions=SAMPLE_TRANSACTIONS,
            summary_metrics=SAMPLE_SUMMARY,
        )

        self.assertTrue(packed.startswith(b"BWRCD"))
        self.assertGreater(len(packed), 37)

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "week_export")
            saved_path = RCDFileManager.save_file(filepath, packed)
            self.assertTrue(saved_path.endswith(".rcd"))

            unpacked = RCDFileManager.unpack_file(saved_path)

        self.assertEqual(unpacked["spec"], "BudgetWise-Weekly-Record")
        self.assertEqual(unpacked["version"], "1.0")
        self.assertEqual(unpacked["user"], "riddhiman_test")
        self.assertEqual(unpacked["period"]["start"], "2026-09-14")
        self.assertEqual(unpacked["period"]["end"], "2026-09-20")
        self.assertEqual(unpacked["summary"], SAMPLE_SUMMARY)
        self.assertEqual(unpacked["records"], SAMPLE_TRANSACTIONS)

    def test_tampered_checksum_rejected(self) -> None:
        packed = bytearray(
            RCDFileManager.pack_weekly_data(
                username="riddhiman_test",
                week_start="2026-09-14",
                week_end="2026-09-20",
                transactions=SAMPLE_TRANSACTIONS,
                summary_metrics=SAMPLE_SUMMARY,
            )
        )
        packed[10] ^= 0xFF

        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "tampered.rcd")
            with open(filepath, "wb") as handle:
                handle.write(packed)

            with self.assertRaises(InvalidRCDFileError):
                RCDFileManager.unpack_file(filepath)

    def test_invalid_header_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "bad_header.rcd")
            with open(filepath, "wb") as handle:
                handle.write(b"BADHD" + b"\x00" * 32 + b"payload")

            with self.assertRaises(InvalidRCDFileError):
                RCDFileManager.unpack_file(filepath)


if __name__ == "__main__":
    unittest.main()
