from datetime import date

import pytest

from reconciler.matcher import _extract_invoice_ref, reconcile
from reconciler.models import Invoice, Transaction


def inv(number: str, amount: float, due: str = "2024-01-01") -> Invoice:
    return Invoice(invoice_number=number, total_amount=amount, due_date=date.fromisoformat(due))


def tx(id: str, amount: float, note: str, d: str = "2024-01-05") -> Transaction:
    return Transaction(id=id, amount=amount, date=date.fromisoformat(d), note=note)


# ── _extract_invoice_ref ────────────────────────────────────────────────────


def test_extracts_standard_reference():
    assert _extract_invoice_ref("Payment for INV-001") == "INV-001"


def test_extracts_multi_digit_reference():
    assert _extract_invoice_ref("Payment for INV-123") == "INV-123"


def test_returns_none_when_no_reference():
    assert _extract_invoice_ref("Refund adjustment") is None


def test_returns_none_for_empty_note():
    assert _extract_invoice_ref("") is None


# ── reconcile ───────────────────────────────────────────────────────────────


def test_exact_match_is_reconciled():
    invoices = [inv("INV-001", 100.0)]
    transactions = [tx("001", 100.0, "Payment for INV-001")]
    report = reconcile(invoices, transactions)
    assert len(report.reconciled) == 1
    assert report.reconciled[0].invoice.invoice_number == "INV-001"
    assert report.reconciled[0].transaction.id == "001"
    assert len(report.unmatched_invoices) == 0
    assert len(report.unmatched_transactions) == 0


def test_amount_mismatch_leaves_both_unmatched():
    invoices = [inv("INV-001", 100.0)]
    transactions = [tx("001", 50.0, "Payment for INV-001")]
    report = reconcile(invoices, transactions)
    assert len(report.reconciled) == 0
    assert len(report.unmatched_invoices) == 1
    assert len(report.unmatched_transactions) == 1


def test_unknown_invoice_reference_is_unmatched_transaction():
    invoices = [inv("INV-001", 100.0)]
    transactions = [tx("003", 100.0, "Payment for INV-216")]
    report = reconcile(invoices, transactions)
    assert len(report.reconciled) == 0
    assert report.unmatched_transactions[0].id == "003"
    assert report.unmatched_invoices[0].invoice_number == "INV-001"


def test_transaction_without_invoice_ref_is_unmatched():
    invoices = [inv("INV-001", 100.0)]
    transactions = [tx("050", 50.0, "Refund adjustment")]
    report = reconcile(invoices, transactions)
    assert len(report.reconciled) == 0
    assert len(report.unmatched_transactions) == 1
    assert len(report.unmatched_invoices) == 1


def test_invoice_without_matching_transaction_is_unmatched():
    invoices = [inv("INV-999", 500.0)]
    transactions = []
    report = reconcile(invoices, transactions)
    assert len(report.unmatched_invoices) == 1
    assert report.unmatched_invoices[0].invoice_number == "INV-999"


def test_multiple_invoices_and_transactions():
    invoices = [inv("INV-001", 100.0), inv("INV-002", 200.0), inv("INV-003", 150.0)]
    transactions = [
        tx("001", 100.0, "Payment for INV-001"),
        tx("002", 200.0, "Payment for INV-002"),
        tx("003", 100.0, "Payment for INV-216"),  # unknown invoice
    ]
    report = reconcile(invoices, transactions)
    assert len(report.reconciled) == 2
    assert len(report.unmatched_invoices) == 1  # INV-003
    assert len(report.unmatched_transactions) == 1  # INV-216


def test_float_precision_tolerance():
    """Amounts that differ only beyond 2 decimal places should still match."""
    invoices = [inv("INV-001", 100.001)]
    transactions = [tx("001", 100.001, "Payment for INV-001")]
    report = reconcile(invoices, transactions)
    assert len(report.reconciled) == 1


def test_invoice_with_invalid_due_date_can_be_reconciled():
    """Invoices with due_date=None (invalid date from CSV) should still match."""
    invoice = Invoice(invoice_number="INV-005", total_amount=300.0, due_date=None)
    transactions = [tx("005", 300.0, "Payment for INV-005")]
    report = reconcile([invoice], transactions)
    assert len(report.reconciled) == 1


def test_empty_inputs():
    report = reconcile([], [])
    assert report.reconciled == []
    assert report.unmatched_invoices == []
    assert report.unmatched_transactions == []
