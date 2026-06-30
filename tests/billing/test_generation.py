from decimal import Decimal

import pytest

from src.billing.generation import (
    InvoiceGenerationError,
    InvoiceGenerationRequest,
    InvoiceGenerator,
)
from src.billing.models import InvoiceStatus
from src.billing.persistence import InvoiceStore


class TestInvoiceGenerator:
    def test_generate_success(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)

        request = InvoiceGenerationRequest(
            customer_id="cust-001",
            line_items=[
                {"description": "Consulting", "amount": "1200.00"},
                {"description": "License", "amount": "300.00"},
            ],
        )

        invoice = generator.generate(request)

        assert invoice.customer_id == "cust-001"
        assert len(invoice.line_items) == 2
        assert invoice.total == Decimal("1500.00")
        assert invoice.status == InvoiceStatus.ISSUED

        loaded = store.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.total == Decimal("1500.00")

    def test_generate_missing_customer_id_raises(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)

        request = InvoiceGenerationRequest(
            customer_id="",
            line_items=[{"description": "Test", "amount": "100"}],
        )

        with pytest.raises(InvoiceGenerationError, match="customer_id is required"):
            generator.generate(request)

    def test_generate_no_line_items_raises(self) -> None:
        store = InvoiceStore()
        generator = InvoiceGenerator(store)

        request = InvoiceGenerationRequest(customer_id="cust-001", line_items=[])

        with pytest.raises(InvoiceGenerationError, match="at least one line item"):
            generator.generate(request)
