import logging
import re

from external_resources.reconciliation_report import ReconciliationReport
from reconciler.models import Invoice, ReconciledPair, Transaction

logger = logging.getLogger(__name__)

_INV_REF_PATTERN = re.compile(r"\bINV-\d+\b")


def _extract_invoice_ref(note: str) -> str | None:
    match = _INV_REF_PATTERN.search(note)
    return match.group(0) if match else None


def reconcile(invoices: list[Invoice], transactions: list[Transaction]) -> ReconciliationReport:
    """
    Match invoices to transactions.

    Matching criteria (identified from data analysis):
      1. Transaction note references the invoice number (e.g. "Payment for INV-001")
      2. Transaction amount equals invoice total_amount (rounded to 2 decimal places)

    Complexity: O(n + m) using a dict index on invoice_number.
    """
    invoice_index: dict[str, Invoice] = {inv.invoice_number: inv for inv in invoices}

    reconciled: list[ReconciledPair] = []
    unmatched_transactions: list[Transaction] = []
    matched_invoice_numbers: set[str] = set()

    for tx in transactions:
        inv_ref = _extract_invoice_ref(tx.note)

        if inv_ref is None:
            logger.info("Transaction %s: no invoice reference in note '%s'", tx.id, tx.note)
            unmatched_transactions.append(tx)
            continue

        invoice = invoice_index.get(inv_ref)

        if invoice is None:
            logger.info("Transaction %s: references unknown invoice %s", tx.id, inv_ref)
            unmatched_transactions.append(tx)
            continue

        if round(invoice.total_amount, 2) != round(tx.amount, 2):
            logger.info(
                "Transaction %s: amount mismatch for %s (invoice=%.2f, tx=%.2f)",
                tx.id, inv_ref, invoice.total_amount, tx.amount,
            )
            unmatched_transactions.append(tx)
            continue

        reconciled.append(ReconciledPair(invoice=invoice, transaction=tx))
        matched_invoice_numbers.add(inv_ref)
        logger.debug("Reconciled %s <-> Transaction %s", inv_ref, tx.id)

    unmatched_invoices: list[Invoice] = [
        inv for inv in invoices if inv.invoice_number not in matched_invoice_numbers
    ]

    logger.info(
        "Reconciliation complete: %d matched, %d unmatched invoices, %d unmatched transactions",
        len(reconciled), len(unmatched_invoices), len(unmatched_transactions),
    )

    return ReconciliationReport(
        reconciled=reconciled,
        unmatched_invoices=unmatched_invoices,
        unmatched_transactions=unmatched_transactions,
    )
