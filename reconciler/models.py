from dataclasses import dataclass
from datetime import date


@dataclass
class Invoice:
    invoice_number: str
    total_amount: float
    due_date: date | None

    def __str__(self) -> str:
        return f"Invoice({self.invoice_number}, amount={self.total_amount}, due={self.due_date})"


@dataclass
class Transaction:
    id: str
    amount: float
    date: date
    note: str

    def __str__(self) -> str:
        return f"Transaction({self.id}, amount={self.amount}, date={self.date}, note='{self.note}')"


@dataclass
class ReconciledPair:
    invoice: Invoice
    transaction: Transaction

    def __str__(self) -> str:
        return f"ReconciledPair({self.invoice.invoice_number} <-> Tx-{self.transaction.id})"
