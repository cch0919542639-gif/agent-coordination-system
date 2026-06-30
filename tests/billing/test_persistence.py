from decimal import Decimal

import pytest

from src.billing.models import Invoice
from src.billing.persistence import InvoiceStore


class TestInvoiceStore:
    def test_save_and_load(self) -> None:
        store = InvoiceStore()
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Setup", Decimal("150.00"))
        store.save(invoice)

        loaded = store.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.customer_id == "cust-001"
        assert loaded.total == Decimal("150.00")

    def test_load_missing_returns_none(self) -> None:
        store = InvoiceStore()
        assert store.load("nonexistent") is None

    def test_delete(self) -> None:
        store = InvoiceStore()
        invoice = Invoice(customer_id="cust-001")
        store.save(invoice)
        store.delete(invoice.invoice_id)
        assert store.load(invoice.invoice_id) is None

    def test_list_by_customer(self) -> None:
        store = InvoiceStore()
        inv1 = Invoice(customer_id="cust-a")
        inv2 = Invoice(customer_id="cust-b")
        inv3 = Invoice(customer_id="cust-a")
        store.save(inv1)
        store.save(inv2)
        store.save(inv3)

        customer_a_invoices = store.list_by_customer("cust-a")
        assert len(customer_a_invoices) == 2

        customer_b_invoices = store.list_by_customer("cust-b")
        assert len(customer_b_invoices) == 1

    def test_count(self) -> None:
        store = InvoiceStore()
        assert store.count() == 0
        store.save(Invoice(customer_id="c1"))
        assert store.count() == 1
        store.save(Invoice(customer_id="c2"))
        assert store.count() == 2

    def test_create_and_load_happy_path(self) -> None:
        store = InvoiceStore()
        invoice = Invoice(customer_id="alice")
        invoice.add_line_item("Consulting", Decimal("1200.00"))
        invoice.add_line_item("License", Decimal("300.00"))
        invoice.issue()
        store.save(invoice)

        loaded = store.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.customer_id == "alice"
        assert len(loaded.line_items) == 2
        assert loaded.total == Decimal("1500.00")
        assert loaded.status.name == "ISSUED"
        assert loaded.balance == Decimal("1500.00")

        loaded.record_payment(Decimal("500.00"))
        assert loaded.paid_amount == Decimal("500.00")
        assert loaded.balance == Decimal("1000.00")
