import csv
import logging
from datetime import date
from pathlib import Path
from typing import Optional

from reconciler.models import Invoice

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> Optional[date]:
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None


def extract_invoices(csv_path: Path) -> list[Invoice]:
    """
    Parse invoices from CSV. Rows with missing/invalid amounts are skipped.
    Rows with invalid dates are included with due_date=None (logged as warnings).
    Malformed rows (wrong column count) are skipped.
    """
    invoices: list[Invoice] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None or not {
            "invoice_number", "total_amount", "due_date"
        }.issubset(reader.fieldnames):
            raise ValueError(f"CSV missing required columns. Found: {reader.fieldnames}")

        for row_num, row in enumerate(reader, start=2):
            invoice_number = (row.get("invoice_number") or "").strip()
            if not invoice_number:
                logger.warning("Row %d: empty invoice_number, skipped", row_num)
                continue

            raw_amount = (row.get("total_amount") or "").strip()
            if not raw_amount:
                logger.warning("Row %d: invoice %s has no amount, skipped", row_num, invoice_number)
                continue

            try:
                total_amount = float(raw_amount)
            except ValueError:
                logger.warning(
                    "Row %d: invoice %s has invalid amount '%s', skipped",
                    row_num, invoice_number, raw_amount,
                )
                continue

            raw_date = (row.get("due_date") or "").strip()
            due_date = _parse_date(raw_date)
            if due_date is None:
                logger.warning(
                    "Row %d: invoice %s has invalid due_date '%s' (included without date)",
                    row_num, invoice_number, raw_date,
                )

            invoices.append(Invoice(
                invoice_number=invoice_number,
                total_amount=total_amount,
                due_date=due_date,
            ))

    logger.info("Extracted %d valid invoices from %s", len(invoices), csv_path)
    return invoices
