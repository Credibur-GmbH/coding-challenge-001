import csv
import logging
from pathlib import Path

from reconciler.models import Invoice
from reconciler.utils import parse_date

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = {"invoice_number", "total_amount", "due_date"}


def _field(row: dict, key: str) -> str:
    return (row.get(key) or "").strip()


def extract_invoices(csv_path: Path) -> list[Invoice]:
    invoices = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if reader.fieldnames is None or not _REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"CSV missing required columns. Found: {reader.fieldnames}")

        for row_num, row in enumerate(reader, start=2):
            invoice_number = _field(row, "invoice_number")
            if not invoice_number:
                logger.warning("Row %d: empty invoice_number, skipped", row_num)
                continue

            raw_amount = _field(row, "total_amount")
            if not raw_amount:
                logger.warning("Row %d: invoice %s has no amount, skipped", row_num, invoice_number)
                continue

            try:
                total_amount = float(raw_amount)
            except ValueError:
                logger.warning("Row %d: invoice %s has invalid amount '%s', skipped", row_num, invoice_number, raw_amount)
                continue

            due_date = parse_date(_field(row, "due_date"))
            if due_date is None:
                logger.warning("Row %d: invoice %s has invalid due_date (included without date)", row_num, invoice_number)

            invoices.append(Invoice(invoice_number=invoice_number, total_amount=total_amount, due_date=due_date))

    logger.info("Extracted %d valid invoices from %s", len(invoices), csv_path)
    return invoices
