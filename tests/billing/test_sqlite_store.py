import os
import tempfile
import threading
from decimal import Decimal

import pytest

from src.billing.models import Invoice, InvoiceStatus
from src.billing.sqlite_store import SCHEMA_VERSION, SqliteInvoiceStore


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

    def test_schema_version_property(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        ver = store.schema_version
        assert ver == 1

    def test_schema_version_constant_matches_store(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        assert store.schema_version == SCHEMA_VERSION

    def test_schema_version_survives_reopen(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        _ = store.schema_version
        del store

        reopened = SqliteInvoiceStore(db_path)
        assert reopened.schema_version == 1

    def test_schema_version_with_existing_data(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Test", Decimal("100.00"))
        store.save(invoice)
        del store

        reopened = SqliteInvoiceStore(db_path)
        assert reopened.schema_version == 1
        loaded = reopened.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.total == Decimal("100.00")

    def test_multiple_inits_idempotent(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        store.save(Invoice(customer_id="c1"))
        del store

        store2 = SqliteInvoiceStore(db_path)
        assert store2.schema_version == 1
        assert store2.count() == 1
        store2.save(Invoice(customer_id="c2"))
        del store2

        store3 = SqliteInvoiceStore(db_path)
        assert store3.schema_version == 1
        assert store3.count() == 2

    def test_concurrency_model_property(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        assert isinstance(store.concurrency_model, str)
        assert len(store.concurrency_model) > 0

    def test_concurrent_writes_serialize_correctly(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        results: list[Exception | None] = [None, None]
        invoices: list[Invoice] = [Invoice(customer_id="alice"), Invoice(customer_id="bob")]
        invoices[0].add_line_item("A", Decimal("100.00"))
        invoices[1].add_line_item("B", Decimal("200.00"))

        def do_save(idx: int) -> None:
            try:
                store.save(invoices[idx])
            except Exception as exc:
                results[idx] = exc

        t1 = threading.Thread(target=do_save, args=(0,))
        t2 = threading.Thread(target=do_save, args=(1,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert results[0] is None
        assert results[1] is None
        assert store.count() == 2
        assert store.load(invoices[0].invoice_id) is not None
        assert store.load(invoices[1].invoice_id) is not None

    def test_separate_instances_same_db(self, db_path: str) -> None:
        store_a = SqliteInvoiceStore(db_path)
        store_b = SqliteInvoiceStore(db_path)

        inv_a = Invoice(customer_id="alice")
        inv_a.add_line_item("X", Decimal("50.00"))
        store_a.save(inv_a)

        inv_b = Invoice(customer_id="bob")
        inv_b.add_line_item("Y", Decimal("75.00"))
        store_b.save(inv_b)

        assert store_a.count() == 2
        assert store_b.count() == 2
        assert store_a.load(inv_a.invoice_id) is not None
        assert store_b.load(inv_b.invoice_id) is not None
