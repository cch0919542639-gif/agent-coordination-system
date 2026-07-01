from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from src.billing.models import InvoiceStatus
from src.billing.persistence import InvoiceStoreProtocol


class BalanceQueryError(Exception):
    pass


@dataclass
class BalanceResult:
    invoice_id: str
    customer_id: str
    total: Decimal
    paid_amount: Decimal
    balance: Decimal
    status: str
    created_at: datetime


class BalanceQuery:
    def __init__(self, store: InvoiceStoreProtocol) -> None:
        self._store = store

    def query(self, invoice_id: str) -> BalanceResult:
        invoice = self._store.load(invoice_id)
        if invoice is None:
            raise BalanceQueryError(f"Invoice not found: {invoice_id}")
        return BalanceResult(
            invoice_id=invoice.invoice_id,
            customer_id=invoice.customer_id,
            total=invoice.total,
            paid_amount=invoice.paid_amount,
            balance=invoice.balance,
            status=invoice.status.value,
            created_at=invoice.created_at,
        )
