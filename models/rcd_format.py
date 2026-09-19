"""BudgetWise .rcd (Record) binary archive format."""

from __future__ import annotations

import gzip
import hashlib
import json
from datetime import datetime, timezone


MAGIC_HEADER = b"BWRCD"
CHECKSUM_SIZE = 32


class InvalidRCDFileError(Exception):
    """Raised when an .rcd file is corrupt, tampered with, or invalid."""


class RCDFileManager:
    """Pack, save, and unpack BudgetWise weekly financial record archives."""

    @staticmethod
    def pack_weekly_data(
        username: str,
        week_start: str,
        week_end: str,
        transactions: list[dict],
        summary_metrics: dict,
    ) -> bytes:
        payload = {
            "spec": "BudgetWise-Weekly-Record",
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "user": username,
            "period": {
                "start": week_start,
                "end": week_end,
            },
            "summary": summary_metrics,
            "records": transactions,
        }

        json_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        compressed = gzip.compress(json_bytes)
        checksum = hashlib.sha256(compressed).digest()

        return MAGIC_HEADER + checksum + compressed

    @staticmethod
    def save_file(filepath: str, rcd_bytes: bytes) -> str:
        if not filepath.lower().endswith(".rcd"):
            filepath = f"{filepath}.rcd"

        with open(filepath, "wb") as handle:
            handle.write(rcd_bytes)

        return filepath

    @staticmethod
    def unpack_file(filepath: str) -> dict:
        with open(filepath, "rb") as handle:
            data = handle.read()

        min_size = len(MAGIC_HEADER) + CHECKSUM_SIZE
        if len(data) < min_size:
            raise InvalidRCDFileError("File is too small to be a valid .rcd archive.")

        if data[: len(MAGIC_HEADER)] != MAGIC_HEADER:
            raise InvalidRCDFileError("Invalid magic header; not a BudgetWise .rcd file.")

        stored_checksum = data[len(MAGIC_HEADER) : len(MAGIC_HEADER) + CHECKSUM_SIZE]
        compressed = data[len(MAGIC_HEADER) + CHECKSUM_SIZE :]

        computed_checksum = hashlib.sha256(compressed).digest()
        if stored_checksum != computed_checksum:
            raise InvalidRCDFileError("Checksum mismatch; file may be corrupt or tampered with.")

        try:
            json_bytes = gzip.decompress(compressed)
            return json.loads(json_bytes.decode("utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidRCDFileError("Unable to decode .rcd payload.") from exc
