from __future__ import annotations

from typing import Dict, List, Optional, Protocol, runtime_checkable

from src.billing.models import Invoice


@runtime_checkable
class InvoiceStoreProtocol(Protocol):
    """Store contract for billing services.

    Any implementation providing these five methods satisfies the contract.
    Both the in-memory ``InvoiceStore`` and the durable ``SqliteInvoiceStore``
    conform to this protocol via structural subtyping.
    """

    def save(self, invoice: Invoice) -> None: ...
    def load(self, invoice_id: str) -> Optional[Invoice]: ...
    def delete(self, invoice_id: str) -> None: ...
    def list_by_customer(self, customer_id: str) -> List[Invoice]: ...
    def count(self) -> int: ...


class InvoiceStore:
    def __init__(self) -> None:
        self._invoices: Dict[str, Invoice] = {}

    def save(self, invoice: Invoice) -> None:
        self._invoices[invoice.invoice_id] = invoice

    def load(self, invoice_id: str) -> Optional[Invoice]:
        return self._invoices.get(invoice_id)

    def delete(self, invoice_id: str) -> None:
        self._invoices.pop(invoice_id, None)

    def list_by_customer(self, customer_id: str) -> List[Invoice]:
        return [inv for inv in self._invoices.values() if inv.customer_id == customer_id]

    def count(self) -> int:
        return len(self._invoices)
