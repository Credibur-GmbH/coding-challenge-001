from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from external_resources.mock_bank_api import MockBankAPIServer, MockHttpResponse
from reconciler.transaction_fetcher import _parse_transactions, fetch_transactions


def _make_api(responses: list[MockHttpResponse]) -> MockBankAPIServer:
    api = MagicMock(spec=MockBankAPIServer)
    api.get_transactions.side_effect = responses
    return api


VALID_TOKEN = "jtX6Qm^kU,%5]uCG"
NO_SLEEP = lambda _: None  # noqa: E731


def _ok(data=None):
    return MockHttpResponse(status_code=200, data=data or [])


def _err500():
    return MockHttpResponse(status_code=500)


def _err401():
    return MockHttpResponse(status_code=401)


# ── fetch_transactions ──────────────────────────────────────────────────────


def test_success_on_first_attempt():
    raw = [{"id": "001", "amount": 100.0, "date": "2024-01-01", "note": "Pay INV-001"}]
    api = _make_api([_ok(raw)])
    result = fetch_transactions(api, VALID_TOKEN, base_delay=0, sleep_fn=NO_SLEEP)
    assert len(result) == 1
    assert result[0].id == "001"


def test_retries_on_500_then_succeeds():
    raw = [{"id": "001", "amount": 50.0, "date": "2024-01-01", "note": "note"}]
    api = _make_api([_err500(), _err500(), _ok(raw)])
    result = fetch_transactions(api, VALID_TOKEN, max_retries=5, base_delay=0, sleep_fn=NO_SLEEP)
    assert len(result) == 1
    assert api.get_transactions.call_count == 3


def test_raises_after_max_retries():
    api = _make_api([_err500()] * 4)
    with pytest.raises(RuntimeError, match="API"):
        fetch_transactions(api, VALID_TOKEN, max_retries=4, base_delay=0, sleep_fn=NO_SLEEP)


def test_raises_permission_error_on_401():
    api = _make_api([_err401()])
    with pytest.raises(PermissionError, match="401"):
        fetch_transactions(api, VALID_TOKEN, base_delay=0, sleep_fn=NO_SLEEP)


def test_exponential_backoff_delays():
    delays = []
    api = _make_api([_err500(), _err500(), _ok()])
    fetch_transactions(api, VALID_TOKEN, max_retries=5, base_delay=1.0, sleep_fn=delays.append)
    assert delays == [1.0, 2.0]  # base * 2^0, base * 2^1


# ── _parse_transactions ─────────────────────────────────────────────────────


def test_negative_amount_skipped():
    raw = [{"id": "001", "amount": -10.0, "date": "2024-01-01", "note": "refund"}]
    result = _parse_transactions(raw)
    assert result == []


def test_invalid_date_skipped():
    raw = [{"id": "049", "amount": 1000.0, "date": "INVALID_DATE", "note": "note"}]
    result = _parse_transactions(raw)
    assert result == []


def test_missing_amount_skipped():
    raw = [{"id": "001", "date": "2024-01-01", "note": "note"}]
    result = _parse_transactions(raw)
    assert result == []


def test_zero_amount_included():
    raw = [{"id": "020", "amount": 0.0, "date": "2024-10-25", "note": "Payment for INV-020"}]
    result = _parse_transactions(raw)
    assert len(result) == 1
    assert result[0].amount == 0.0


def test_valid_transaction_fields():
    raw = [{"id": "007", "amount": 180.0, "date": "2024-08-20", "note": "Payment for INV-007"}]
    result = _parse_transactions(raw)
    assert result[0].id == "007"
    assert result[0].amount == 180.0
    assert result[0].date == date(2024, 8, 20)
    assert result[0].note == "Payment for INV-007"
