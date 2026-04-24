import csv
import logging
from pathlib import Path

from external_resources.reconciliation_report import ReconciliationReport
from reconciler.models import Invoice, ReconciledPair, Transaction

logger = logging.getLogger(__name__)


def write_csv_report(report: ReconciliationReport, output_dir: Path) -> None:
    """Write reconciled, unmatched_invoices, and unmatched_transactions to separate CSVs."""
    output_dir.mkdir(parents=True, exist_ok=True)

    reconciled_path = output_dir / "reconciled.csv"
    unmatched_inv_path = output_dir / "unmatched_invoices.csv"
    unmatched_tx_path = output_dir / "unmatched_transactions.csv"

    _write_reconciled(report.reconciled, reconciled_path)
    _write_unmatched_invoices(report.unmatched_invoices, unmatched_inv_path)
    _write_unmatched_transactions(report.unmatched_transactions, unmatched_tx_path)

    logger.info(
        "CSV reports written to %s: reconciled=%d, unmatched_invoices=%d, unmatched_transactions=%d",
        output_dir,
        len(report.reconciled),
        len(report.unmatched_invoices),
        len(report.unmatched_transactions),
    )


def _write_reconciled(pairs: list, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "invoice_number", "invoice_amount", "invoice_due_date",
            "transaction_id", "transaction_amount", "transaction_date", "transaction_note",
        ])
        for pair in pairs:
            inv: Invoice = pair.invoice
            tx: Transaction = pair.transaction
            writer.writerow([
                inv.invoice_number,
                f"{inv.total_amount:.2f}",
                inv.due_date or "",
                tx.id,
                f"{tx.amount:.2f}",
                tx.date,
                tx.note,
            ])


def _write_unmatched_invoices(invoices: list, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["invoice_number", "total_amount", "due_date"])
        for inv in invoices:
            writer.writerow([inv.invoice_number, f"{inv.total_amount:.2f}", inv.due_date or ""])


def _write_unmatched_transactions(transactions: list, path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["transaction_id", "amount", "date", "note"])
        for tx in transactions:
            writer.writerow([tx.id, f"{tx.amount:.2f}", tx.date, tx.note])
