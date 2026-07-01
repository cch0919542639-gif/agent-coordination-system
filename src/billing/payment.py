from __future__ import annotations

from decimal import Decimal

from src.billing.models import Invoice
from src.billing.persistence import InvoiceStoreProtocol


class PaymentRecordError(Exception):
    pass


class PaymentRecorder:
    def __init__(self, store: InvoiceStoreProtocol) -> None:
        self._store = store

    def record_payment(self, invoice_id: str, amount: Decimal) -> Invoice:
        invoice = self._store.load(invoice_id)
        if invoice is None:
            raise PaymentRecordError(f"Invoice not found: {invoice_id}")
        try:
            invoice.record_payment(amount)
        except ValueError as exc:
            raise PaymentRecordError(str(exc)) from exc
        self._store.save(invoice)
        return invoice
