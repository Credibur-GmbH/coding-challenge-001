import logging
import sys
from pathlib import Path

from external_resources.invoice_data import INVOICE_DATA_CSV_PATH
from external_resources.mock_bank_api import MockBankAPIServer
from external_resources.secrets import MOCK_BANK_API_TOKENS
from reconciler.invoice_extractor import extract_invoices
from reconciler.matcher import reconcile
from reconciler.report_writer import write_csv_report
from reconciler.transaction_fetcher import fetch_transactions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def run(output_dir: Path = Path("reports")) -> None:
    logger.info("=== Invoice Reconciliation Pipeline ===")

    logger.info("Step 1: Extracting invoices from %s", INVOICE_DATA_CSV_PATH)
    invoices = extract_invoices(INVOICE_DATA_CSV_PATH)

    logger.info("Step 2: Fetching bank transactions from API")
    api = MockBankAPIServer()
    auth_token = next(iter(MOCK_BANK_API_TOKENS))
    transactions = fetch_transactions(api, auth_token)

    logger.info("Step 3: Reconciling %d invoices against %d transactions", len(invoices), len(transactions))
    report = reconcile(invoices, transactions)

    report.print_report()

    logger.info("Step 4: Writing CSV reports to '%s/'", output_dir)
    write_csv_report(report, output_dir)

    logger.info("=== Pipeline complete ===")


if __name__ == "__main__":
    run()
