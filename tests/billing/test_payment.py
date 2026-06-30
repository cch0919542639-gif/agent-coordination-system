from decimal import Decimal

import pytest

from src.billing.generation import InvoiceGenerationRequest, InvoiceGenerator
from src.billing.models import Invoice, InvoiceStatus
from src.billing.payment import PaymentRecordError, PaymentRecorder
from src.billing.persistence import InvoiceStore


class TestPaymentRecorder:
    def test_record_partial_payment(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)
        request = InvoiceGenerationRequest(
            customer_id="cust-001",
            line_items=[{"description": "Service", "amount": "1000.00"}],
        )
        invoice = generator.generate(request)

        recorder = PaymentRecorder(store)
        updated = recorder.record_payment(invoice.invoice_id, Decimal("400.00"))

        assert updated.paid_amount == Decimal("400.00")
        assert updated.balance == Decimal("600.00")
        assert updated.status == InvoiceStatus.ISSUED

    def test_record_full_payment(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)
        request = InvoiceGenerationRequest(
            customer_id="cust-001",
            line_items=[{"description": "Service", "amount": "500.00"}],
        )
        invoice = generator.generate(request)

        recorder = PaymentRecorder(store)
        updated = recorder.record_payment(invoice.invoice_id, Decimal("500.00"))

        assert updated.paid_amount == Decimal("500.00")
        assert updated.balance == Decimal("0")
        assert updated.status == InvoiceStatus.PAID

    def test_invoice_not_found_raises(self) -> None:
        store = InvoiceStore()
        recorder = PaymentRecorder(store)

        with pytest.raises(PaymentRecordError, match="not found"):
            recorder.record_payment("nonexistent", Decimal("100"))

    def test_negative_amount_raises(self) -> None:
        store = InvoiceStore()
        invoice = Invoice(customer_id="c1")
        invoice.add_line_item("Test", Decimal("100"))
        invoice.issue()
        store.save(invoice)

        recorder = PaymentRecorder(store)
        with pytest.raises(PaymentRecordError, match="positive"):
            recorder.record_payment(invoice.invoice_id, Decimal("-50"))

    def test_draft_invoice_raises(self) -> None:
        store = InvoiceStore()
        invoice = Invoice(customer_id="c1")
        invoice.add_line_item("Test", Decimal("100"))
        store.save(invoice)

        recorder = PaymentRecorder(store)
        with pytest.raises(PaymentRecordError, match="Cannot pay a draft"):
            recorder.record_payment(invoice.invoice_id, Decimal("50"))

    def test_cancelled_invoice_raises(self) -> None:
        store = InvoiceStore()
        invoice = Invoice(customer_id="c1")
        invoice.add_line_item("Test", Decimal("100"))
        invoice.issue()
        invoice.cancel()
        store.save(invoice)

        recorder = PaymentRecorder(store)
        with pytest.raises(PaymentRecordError, match="cancelled"):
            recorder.record_payment(invoice.invoice_id, Decimal("50"))

    def test_overpayment_raises(self) -> None:
        store = InvoiceStore()
        invoice = Invoice(customer_id="c1")
        invoice.add_line_item("Test", Decimal("100"))
        invoice.issue()
        store.save(invoice)

        recorder = PaymentRecorder(store)
        with pytest.raises(PaymentRecordError, match="exceeds"):
            recorder.record_payment(invoice.invoice_id, Decimal("200"))
