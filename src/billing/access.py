from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from src.billing.models import Invoice
from src.billing.persistence import InvoiceStoreProtocol
from src.billing.queries import BalanceQuery, BalanceQueryError, BalanceResult


@dataclass(frozen=True)
class CustomerAccess:
    customer_id: str


class CustomerBoundary:
    def __init__(self, store: InvoiceStoreProtocol, access: CustomerAccess) -> None:
        self._store = store
        self._access = access

    @property
    def customer_id(self) -> str:
        return self._access.customer_id

    def list_invoices(self) -> List[Invoice]:
        return self._store.list_by_customer(self._access.customer_id)

    def load_invoice(self, invoice_id: str) -> Optional[Invoice]:
        invoice = self._store.load(invoice_id)
        if invoice is None or invoice.customer_id != self._access.customer_id:
            return None
        return invoice

    def query_balance(self, invoice_id: str) -> BalanceResult:
        invoice = self.load_invoice(invoice_id)
        if invoice is None:
            raise BalanceQueryError(
                f"Invoice {invoice_id} not found or not accessible"
            )
        return BalanceResult(
            invoice_id=invoice.invoice_id,
            customer_id=invoice.customer_id,
            total=invoice.total,
            paid_amount=invoice.paid_amount,
            balance=invoice.balance,
            status=invoice.status.value,
            created_at=invoice.created_at,
        )
