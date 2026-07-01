from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

from src.billing.models import Invoice, InvoiceLineItem
from src.billing.persistence import InvoiceStoreProtocol


class InvoiceGenerationError(Exception):
    pass


@dataclass
class InvoiceGenerationRequest:
    customer_id: str
    line_items: List[dict] = field(default_factory=list)


class InvoiceGenerator:
    def __init__(self, store: InvoiceStoreProtocol) -> None:
        self._store = store

    def generate(self, request: InvoiceGenerationRequest) -> Invoice:
        if not request.customer_id:
            raise InvoiceGenerationError("customer_id is required")

        if not request.line_items:
            raise InvoiceGenerationError("at least one line item is required")

        invoice = Invoice(customer_id=request.customer_id)

        for item in request.line_items:
            description = item.get("description", "")
            amount = Decimal(str(item.get("amount", "0")))
            invoice.add_line_item(description, amount)

        invoice.issue()
        self._store.save(invoice)
        return invoice
