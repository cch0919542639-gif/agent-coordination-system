from __future__ import annotations

from typing import Dict, Optional

from src.billing.models import Invoice


class InvoiceStore:
    def __init__(self) -> None:
        self._invoices: Dict[str, Invoice] = {}

    def save(self, invoice: Invoice) -> None:
        self._invoices[invoice.invoice_id] = invoice

    def load(self, invoice_id: str) -> Optional[Invoice]:
        return self._invoices.get(invoice_id)

    def delete(self, invoice_id: str) -> None:
        self._invoices.pop(invoice_id, None)

    def list_by_customer(self, customer_id: str) -> list[Invoice]:
        return [inv for inv in self._invoices.values() if inv.customer_id == customer_id]

    def count(self) -> int:
        return len(self._invoices)
