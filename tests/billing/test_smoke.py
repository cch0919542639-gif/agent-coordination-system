"""Smoke test: generate invoice -> record payment -> query balance."""

from decimal import Decimal

from src.billing.generation import InvoiceGenerationRequest, InvoiceGenerator
from src.billing.payment import PaymentRecorder
from src.billing.persistence import InvoiceStore
from src.billing.queries import BalanceQuery


class TestBillingSmoke:
    def test_generate_pay_query_partial_payment(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)
        recorder = PaymentRecorder(store)
        query = BalanceQuery(store)

        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="smoke-customer",
                line_items=[
                    {"description": "Consulting", "amount": "2000.00"},
                    {"description": "License", "amount": "500.00"},
                ],
            )
        )
        assert invoice.total == Decimal("2500.00")
        assert invoice.balance == Decimal("2500.00")
        assert invoice.paid_amount == Decimal("0")

        updated = recorder.record_payment(invoice.invoice_id, Decimal("1000.00"))
        assert updated.paid_amount == Decimal("1000.00")
        assert updated.balance == Decimal("1500.00")

        result = query.query(invoice.invoice_id)
        assert result.invoice_id == invoice.invoice_id
        assert result.customer_id == "smoke-customer"
        assert result.total == Decimal("2500.00")
        assert result.paid_amount == Decimal("1000.00")
        assert result.balance == Decimal("1500.00")
        assert result.status == "issued"

    def test_generate_pay_query_full_payment(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)
        recorder = PaymentRecorder(store)
        query = BalanceQuery(store)

        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="smoke-customer",
                line_items=[{"description": "Service", "amount": "750.00"}],
            )
        )
        assert invoice.total == Decimal("750.00")
        assert invoice.status.value == "issued"

        updated = recorder.record_payment(invoice.invoice_id, Decimal("750.00"))
        assert updated.paid_amount == Decimal("750.00")
        assert updated.balance == Decimal("0")
        assert updated.status.value == "paid"

        result = query.query(invoice.invoice_id)
        assert result.total == Decimal("750.00")
        assert result.paid_amount == Decimal("750.00")
        assert result.balance == Decimal("0")
        assert result.status == "paid"
