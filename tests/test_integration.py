"""
Integration tests: run the full pipeline end-to-end using the real CSV
and the MockBankAPIServer.
"""
import csv
from pathlib import Path

from external_resources.invoice_data import INVOICE_DATA_CSV_PATH
from external_resources.mock_bank_api import MockBankAPIServer, MockHttpResponse
from external_resources.secrets import MOCK_BANK_API_TOKENS
from reconciler.invoice_extractor import extract_invoices
from reconciler.matcher import reconcile
from reconciler.report_writer import write_csv_report
from reconciler.transaction_fetcher import fetch_transactions


def _always_ok_api() -> MockBankAPIServer:
    """MockBankAPIServer that always returns 200 (no random 500 errors)."""
    api = MockBankAPIServer()

    def get_transactions(request):
        if request.get("Headers", {}).get("auth_token") not in MOCK_BANK_API_TOKENS:
            return MockHttpResponse(status_code=401)
        return MockHttpResponse(status_code=200, data=MockBankAPIServer._get_mock_transactions_data())

    api.get_transactions = get_transactions
    return api


_NO_SLEEP = lambda _: None  # noqa: E731
_TOKEN = next(iter(MOCK_BANK_API_TOKENS))


def _run_pipeline():
    invoices = extract_invoices(INVOICE_DATA_CSV_PATH)
    transactions = fetch_transactions(_always_ok_api(), _TOKEN, base_delay=0, sleep_fn=_NO_SLEEP)
    report = reconcile(invoices, transactions)
    return invoices, transactions, report


def test_invoice_extraction_count():
    # 49 data rows; 3 skipped: INV-004 (no amount), INV-020 (no amount), BROKEN_ROW (no amount)
    invoices = extract_invoices(INVOICE_DATA_CSV_PATH)
    assert len(invoices) == 46


def test_transaction_fetch_count():
    # 50 raw transactions; 2 skipped: Tx-049 (invalid date), Tx-050 (negative amount)
    transactions = fetch_transactions(_always_ok_api(), _TOKEN, base_delay=0, sleep_fn=_NO_SLEEP)
    assert len(transactions) == 48


def test_full_pipeline_reconciliation_counts():
    _, _, report = _run_pipeline()
    # 45 matched pairs; INV-001 has amount mismatch (invoice=100, tx=50)
    assert len(report.reconciled) == 45
    assert len(report.unmatched_invoices) == 1
    assert len(report.unmatched_transactions) == 3


def test_inv001_is_unmatched_due_to_amount_mismatch():
    _, _, report = _run_pipeline()
    reconciled_numbers = {p.invoice.invoice_number for p in report.reconciled}
    assert "INV-001" not in reconciled_numbers
    unmatched_numbers = {inv.invoice_number for inv in report.unmatched_invoices}
    assert "INV-001" in unmatched_numbers


def test_invoices_with_invalid_dates_are_reconciled():
    """INV-005 and INV-033 have INVALID_DATE in CSV but should still reconcile by amount."""
    _, _, report = _run_pipeline()
    reconciled_numbers = {p.invoice.invoice_number for p in report.reconciled}
    assert "INV-005" in reconciled_numbers
    assert "INV-033" in reconciled_numbers


def test_unmatched_transaction_ids():
    _, _, report = _run_pipeline()
    unmatched_ids = {tx.id for tx in report.unmatched_transactions}
    assert "001" in unmatched_ids   # amount mismatch with INV-001 (invoice=100, tx=50)
    assert "003" in unmatched_ids   # references INV-216 (no such invoice)
    assert "020" in unmatched_ids   # references INV-020 (skipped — no amount in CSV)


def test_invalid_invoices_excluded():
    """INV-004 and INV-020 (missing amounts) must not appear anywhere in the report."""
    _, _, report = _run_pipeline()
    all_invoice_numbers = (
        {p.invoice.invoice_number for p in report.reconciled}
        | {inv.invoice_number for inv in report.unmatched_invoices}
    )
    assert "INV-004" not in all_invoice_numbers
    assert "INV-020" not in all_invoice_numbers


def test_csv_report_files_written(tmp_path):
    _, _, report = _run_pipeline()
    write_csv_report(report, tmp_path)

    reconciled_path = tmp_path / "reconciled.csv"
    unmatched_inv_path = tmp_path / "unmatched_invoices.csv"
    unmatched_tx_path = tmp_path / "unmatched_transactions.csv"

    assert reconciled_path.exists()
    assert unmatched_inv_path.exists()
    assert unmatched_tx_path.exists()

    with open(reconciled_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(report.reconciled)
    assert set(rows[0].keys()) == {
        "invoice_number", "invoice_amount", "invoice_due_date",
        "transaction_id", "transaction_amount", "transaction_date", "transaction_note",
    }

    with open(unmatched_inv_path, encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == len(report.unmatched_invoices)

    with open(unmatched_tx_path, encoding="utf-8") as f:
        assert len(list(csv.DictReader(f))) == len(report.unmatched_transactions)


def test_api_retry_eventually_succeeds():
    """Pipeline completes correctly even when the API returns several 500s first."""
    call_count = 0
    real_data = MockBankAPIServer._get_mock_transactions_data()

    def flaky_get_transactions(request):
        nonlocal call_count
        call_count += 1
        if call_count < 4:
            return MockHttpResponse(status_code=500)
        if request.get("Headers", {}).get("auth_token") not in MOCK_BANK_API_TOKENS:
            return MockHttpResponse(status_code=401)
        return MockHttpResponse(status_code=200, data=real_data)

    api = MockBankAPIServer()
    api.get_transactions = flaky_get_transactions

    transactions = fetch_transactions(api, _TOKEN, max_retries=8, base_delay=0, sleep_fn=_NO_SLEEP)
    assert len(transactions) == 48
    assert call_count == 4
