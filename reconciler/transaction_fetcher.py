import logging
import time
from typing import Callable

from external_resources.mock_bank_api import MockBankAPIServer
from reconciler.models import Transaction
from reconciler.utils import parse_date

logger = logging.getLogger(__name__)

_MAX_RETRIES = 8
_BASE_DELAY = 0.5  # seconds; doubles each retry (exponential backoff)


def fetch_transactions(
    api: MockBankAPIServer,
    auth_token: str,
    max_retries: int = _MAX_RETRIES,
    base_delay: float = _BASE_DELAY,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> list[Transaction]:
    request = {"Headers": {"auth_token": auth_token}}

    for attempt in range(max_retries):
        response = api.get_transactions(request)

        if response.status_code == 200:
            transactions = _parse_transactions(response.json() or [])
            logger.info("Fetched %d valid transactions from API", len(transactions))
            return transactions

        if response.status_code == 401:
            raise PermissionError("Invalid API auth token (HTTP 401)")

        if response.status_code == 500 and attempt < max_retries - 1:
            delay = base_delay * (2 ** attempt)
            logger.warning("API returned 500 (attempt %d/%d), retrying in %.2fs", attempt + 1, max_retries, delay)
            sleep_fn(delay)
            continue

        raise RuntimeError(f"API request failed with status {response.status_code} after {attempt + 1} attempt(s)")


def _parse_transactions(raw: list[dict]) -> list[Transaction]:
    transactions = []

    for item in raw:
        tx_id = str(item.get("id", "unknown"))

        try:
            amount = float(item["amount"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Transaction %s: missing or invalid amount, skipped", tx_id)
            continue

        if amount < 0:
            logger.warning("Transaction %s: negative amount %.2f, skipped", tx_id, amount)
            continue

        tx_date = parse_date(str(item.get("date", "")))
        if tx_date is None:
            logger.warning("Transaction %s: invalid date '%s', skipped", tx_id, item.get("date"))
            continue

        transactions.append(Transaction(id=tx_id, amount=amount, date=tx_date, note=str(item.get("note", ""))))

    return transactions
