import textwrap
from datetime import date
from pathlib import Path

import pytest

from reconciler.invoice_extractor import extract_invoices


def _write_csv(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "invoices.csv"
    p.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")
    return p


def test_valid_rows(tmp_path):
    csv = _write_csv(tmp_path, """
        invoice_number,total_amount,due_date
        INV-001,100.00,2024-07-01
        INV-002,200.00,2024-08-01
    """)
    invoices = extract_invoices(csv)
    assert len(invoices) == 2
    assert invoices[0].invoice_number == "INV-001"
    assert invoices[0].total_amount == 100.0
    assert invoices[0].due_date == date(2024, 7, 1)
    assert invoices[1].invoice_number == "INV-002"


def test_row_missing_amount_is_skipped(tmp_path):
    csv = _write_csv(tmp_path, """
        invoice_number,total_amount,due_date
        INV-001,,2024-07-01
        INV-002,200.00,2024-08-01
    """)
    invoices = extract_invoices(csv)
    assert len(invoices) == 1
    assert invoices[0].invoice_number == "INV-002"


def test_row_invalid_amount_is_skipped(tmp_path):
    csv = _write_csv(tmp_path, """
        invoice_number,total_amount,due_date
        INV-001,NOT_A_NUMBER,2024-07-01
        INV-002,50.00,2024-07-15
    """)
    invoices = extract_invoices(csv)
    assert len(invoices) == 1
    assert invoices[0].invoice_number == "INV-002"


def test_row_invalid_date_included_with_none(tmp_path, caplog):
    csv = _write_csv(tmp_path, """
        invoice_number,total_amount,due_date
        INV-001,100.00,INVALID_DATE
    """)
    invoices = extract_invoices(csv)
    assert len(invoices) == 1
    assert invoices[0].due_date is None
    assert "invalid due_date" in caplog.text.lower()


def test_malformed_row_skipped(tmp_path):
    """A row with fewer columns than the header fills missing fields with None."""
    csv = _write_csv(tmp_path, """
        invoice_number,total_amount,due_date
        BROKEN_ROW
        INV-002,200.00,2024-08-01
    """)
    invoices = extract_invoices(csv)
    # BROKEN_ROW has no amount → skipped
    assert len(invoices) == 1
    assert invoices[0].invoice_number == "INV-002"


def test_empty_invoice_number_skipped(tmp_path):
    csv = _write_csv(tmp_path, """
        invoice_number,total_amount,due_date
        ,100.00,2024-07-01
        INV-001,200.00,2024-07-10
    """)
    invoices = extract_invoices(csv)
    assert len(invoices) == 1
    assert invoices[0].invoice_number == "INV-001"


def test_missing_required_columns_raises(tmp_path):
    csv = _write_csv(tmp_path, """
        number,amount
        INV-001,100.00
    """)
    with pytest.raises(ValueError, match="missing required columns"):
        extract_invoices(csv)


def test_real_csv_file():
    """Integration-style: parse the actual invoice_data.csv."""
    from external_resources.invoice_data import INVOICE_DATA_CSV_PATH

    invoices = extract_invoices(INVOICE_DATA_CSV_PATH)

    # 49 data rows in CSV; 3 skipped (INV-004 no amount, INV-020 no amount, BROKEN_ROW)
    assert len(invoices) == 46

    numbers = {inv.invoice_number for inv in invoices}
    assert "INV-004" not in numbers   # missing amount
    assert "INV-020" not in numbers   # missing amount
    assert "BROKEN_ROW" not in numbers

    # INV-005 and INV-033 have INVALID_DATE but are included
    inv_005 = next(i for i in invoices if i.invoice_number == "INV-005")
    assert inv_005.due_date is None
    inv_033 = next(i for i in invoices if i.invoice_number == "INV-033")
    assert inv_033.due_date is None
