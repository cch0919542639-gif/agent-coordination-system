from decimal import Decimal

import pytest

from src.billing.generation import InvoiceGenerationRequest, InvoiceGenerator
from src.billing.models import Invoice
from src.billing.payment import PaymentRecorder
from src.billing.persistence import InvoiceStore
from src.billing.queries import BalanceQuery, BalanceQueryError


class TestBalanceQuery:
    def test_unpaid_invoice(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)
        request = InvoiceGenerationRequest(
            customer_id="cust-001",
            line_items=[{"description": "Service", "amount": "1000.00"}],
        )
        invoice = generator.generate(request)

        query = BalanceQuery(store)
        result = query.query(invoice.invoice_id)

        assert result.customer_id == "cust-001"
        assert result.total == Decimal("1000.00")
        assert result.paid_amount == Decimal("0")
        assert result.balance == Decimal("1000.00")
        assert result.status == "issued"

    def test_partially_paid_invoice(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)
        request = InvoiceGenerationRequest(
            customer_id="cust-001",
            line_items=[{"description": "Service", "amount": "1000.00"}],
        )
        invoice = generator.generate(request)

        recorder = PaymentRecorder(store)
        recorder.record_payment(invoice.invoice_id, Decimal("400.00"))

        query = BalanceQuery(store)
        result = query.query(invoice.invoice_id)

        assert result.total == Decimal("1000.00")
        assert result.paid_amount == Decimal("400.00")
        assert result.balance == Decimal("600.00")
        assert result.status == "issued"

    def test_fully_paid_invoice(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)
        request = InvoiceGenerationRequest(
            customer_id="cust-001",
            line_items=[{"description": "Service", "amount": "500.00"}],
        )
        invoice = generator.generate(request)

        recorder = PaymentRecorder(store)
        recorder.record_payment(invoice.invoice_id, Decimal("500.00"))

        query = BalanceQuery(store)
        result = query.query(invoice.invoice_id)

        assert result.total == Decimal("500.00")
        assert result.paid_amount == Decimal("500.00")
        assert result.balance == Decimal("0")
        assert result.status == "paid"

    def test_invoice_not_found_raises(self) -> None:
        store = InvoiceStore()
        query = BalanceQuery(store)

        with pytest.raises(BalanceQueryError, match="not found"):
            query.query("nonexistent")
