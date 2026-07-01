import os
import tempfile
from decimal import Decimal

import pytest

from src.billing.models import Invoice, InvoiceStatus
from src.billing.sqlite_store import SqliteInvoiceStore


@pytest.fixture
def db_path() -> str:
    tmp = tempfile.mktemp(suffix=".db")
    yield tmp
    try:
        os.remove(tmp)
    except PermissionError:
        pass


class TestSqliteInvoiceStore:
    def test_save_and_load(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Setup", Decimal("150.00"))
        store.save(invoice)

        loaded = store.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.customer_id == "cust-001"
        assert loaded.total == Decimal("150.00")

    def test_load_missing_returns_none(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        assert store.load("nonexistent") is None

    def test_delete(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        invoice = Invoice(customer_id="cust-001")
        store.save(invoice)
        store.delete(invoice.invoice_id)
        assert store.load(invoice.invoice_id) is None

    def test_list_by_customer(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        inv1 = Invoice(customer_id="cust-a")
        inv2 = Invoice(customer_id="cust-b")
        inv3 = Invoice(customer_id="cust-a")
        store.save(inv1)
        store.save(inv2)
        store.save(inv3)

        customer_a = store.list_by_customer("cust-a")
        assert len(customer_a) == 2

        customer_b = store.list_by_customer("cust-b")
        assert len(customer_b) == 1

    def test_count(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        assert store.count() == 0
        store.save(Invoice(customer_id="c1"))
        assert store.count() == 1
        store.save(Invoice(customer_id="c2"))
        assert store.count() == 2

    def test_full_lifecycle_happy_path(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
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
        assert loaded.status == InvoiceStatus.ISSUED
        assert loaded.balance == Decimal("1500.00")

        loaded.record_payment(Decimal("500.00"))
        store.save(loaded)
        updated = store.load(invoice.invoice_id)
        assert updated is not None
        assert updated.paid_amount == Decimal("500.00")
        assert updated.balance == Decimal("1000.00")

    def test_survives_reopen(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Service", Decimal("500.00"))
        invoice.issue()
        store.save(invoice)

        del store

        reopened = SqliteInvoiceStore(db_path)
        loaded = reopened.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.customer_id == "cust-001"
        assert loaded.total == Decimal("500.00")
        assert loaded.status == InvoiceStatus.ISSUED
        assert loaded.balance == Decimal("500.00")

    def test_survives_reopen_with_payment(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Service", Decimal("1000.00"))
        invoice.issue()
        invoice.record_payment(Decimal("400.00"))
        store.save(invoice)
        del store

        reopened = SqliteInvoiceStore(db_path)
        loaded = reopened.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.paid_amount == Decimal("400.00")
        assert loaded.balance == Decimal("600.00")
        assert loaded.status == InvoiceStatus.ISSUED

        loaded.record_payment(Decimal("600.00"))
        reopened.save(loaded)
        del reopened

        reopened2 = SqliteInvoiceStore(db_path)
        final = reopened2.load(invoice.invoice_id)
        assert final is not None
        assert final.paid_amount == Decimal("1000.00")
        assert final.balance == Decimal("0")
        assert final.status == InvoiceStatus.PAID
