import csv
import logging
from pathlib import Path
from typing import Iterable

from external_resources.reconciliation_report import ReconciliationReport

logger = logging.getLogger(__name__)

_RECONCILED_HEADER = [
    "invoice_number", "invoice_amount", "invoice_due_date",
    "transaction_id", "transaction_amount", "transaction_date", "transaction_note",
]
_INVOICE_HEADER = ["invoice_number", "total_amount", "due_date"]
_TX_HEADER = ["transaction_id", "amount", "date", "note"]


def _write_csv_file(path: Path, header: list[str], rows: Iterable) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def write_csv_report(report: ReconciliationReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_csv_file(
        output_dir / "reconciled.csv",
        _RECONCILED_HEADER,
        ([p.invoice.invoice_number, f"{p.invoice.total_amount:.2f}", p.invoice.due_date or "",
          p.transaction.id, f"{p.transaction.amount:.2f}", p.transaction.date, p.transaction.note]
         for p in report.reconciled),
    )
    _write_csv_file(
        output_dir / "unmatched_invoices.csv",
        _INVOICE_HEADER,
        ([inv.invoice_number, f"{inv.total_amount:.2f}", inv.due_date or ""]
         for inv in report.unmatched_invoices),
    )
    _write_csv_file(
        output_dir / "unmatched_transactions.csv",
        _TX_HEADER,
        ([tx.id, f"{tx.amount:.2f}", tx.date, tx.note]
         for tx in report.unmatched_transactions),
    )

    logger.info(
        "CSV reports written to %s: reconciled=%d, unmatched_invoices=%d, unmatched_transactions=%d",
        output_dir,
        len(report.reconciled),
        len(report.unmatched_invoices),
        len(report.unmatched_transactions),
    )
