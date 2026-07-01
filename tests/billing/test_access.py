import os
import tempfile
from decimal import Decimal

import pytest

from src.billing.access import CustomerAccess, CustomerBoundary
from src.billing.models import Invoice, InvoiceStatus
from src.billing.persistence import InvoiceStore
from src.billing.queries import BalanceQueryError
from src.billing.sqlite_store import SqliteInvoiceStore


class TestCustomerAccess:
    def test_value_object(self) -> None:
        access = CustomerAccess("cust-001")
        assert access.customer_id == "cust-001"

    def test_immutable(self) -> None:
        access = CustomerAccess("x")
        with pytest.raises(AttributeError):
            access.customer_id = "y"  # type: ignore[misc]


class TestCustomerBoundaryWithInMemory:
    @pytest.fixture
    def store(self) -> InvoiceStore:
        return InvoiceStore()

    def test_list_invoices_scoped(self, store: InvoiceStore) -> None:
        inv_a = Invoice(customer_id="alice")
        inv_b = Invoice(customer_id="bob")
        store.save(inv_a)
        store.save(inv_b)

        alice = CustomerBoundary(store, CustomerAccess("alice"))
        invoices = alice.list_invoices()
        assert len(invoices) == 1
        assert invoices[0].customer_id == "alice"

    def test_load_invoice_wrong_customer_returns_none(self, store: InvoiceStore) -> None:
        inv = Invoice(customer_id="alice")
        store.save(inv)

        bob = CustomerBoundary(store, CustomerAccess("bob"))
        assert bob.load_invoice(inv.invoice_id) is None

    def test_load_invoice_correct_customer(self, store: InvoiceStore) -> None:
        inv = Invoice(customer_id="alice")
        store.save(inv)

        alice = CustomerBoundary(store, CustomerAccess("alice"))
        loaded = alice.load_invoice(inv.invoice_id)
        assert loaded is not None
        assert loaded.customer_id == "alice"

    def test_load_invoice_not_found(self, store: InvoiceStore) -> None:
        alice = CustomerBoundary(store, CustomerAccess("alice"))
        assert alice.load_invoice("nonexistent") is None

    def test_query_balance_scoped(self, store: InvoiceStore) -> None:
        inv = Invoice(customer_id="alice")
        inv.add_line_item("X", Decimal("100.00"))
        inv.issue()
        store.save(inv)

        alice = CustomerBoundary(store, CustomerAccess("alice"))
        result = alice.query_balance(inv.invoice_id)
        assert result.customer_id == "alice"
        assert result.total == Decimal("100.00")

    def test_query_balance_wrong_customer_raises(self, store: InvoiceStore) -> None:
        inv = Invoice(customer_id="alice")
        inv.add_line_item("X", Decimal("100.00"))
        inv.issue()
        store.save(inv)

        bob = CustomerBoundary(store, CustomerAccess("bob"))
        with pytest.raises(BalanceQueryError):
            bob.query_balance(inv.invoice_id)

    def test_for_customer_factory(self, store: InvoiceStore) -> None:
        inv = Invoice(customer_id="alice")
        store.save(inv)

        boundary = store.for_customer("alice")
        assert isinstance(boundary, CustomerBoundary)
        assert boundary.customer_id == "alice"
        assert len(boundary.list_invoices()) == 1


class TestCustomerBoundaryWithSqlite:
    @pytest.fixture
    def db_path(self) -> str:
        tmp = tempfile.mktemp(suffix=".db")
        yield tmp
        try:
            os.remove(tmp)
        except PermissionError:
            pass

    def test_for_customer_factory(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        inv = Invoice(customer_id="alice")
        store.save(inv)

        boundary = store.for_customer("alice")
        assert isinstance(boundary, CustomerBoundary)
        assert boundary.customer_id == "alice"
        assert len(boundary.list_invoices()) == 1

    def test_customer_isolation(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        inv_a = Invoice(customer_id="alice")
        inv_a.add_line_item("A", Decimal("50.00"))
        inv_a.issue()
        inv_b = Invoice(customer_id="bob")
        inv_b.add_line_item("B", Decimal("75.00"))
        inv_b.issue()
        store.save(inv_a)
        store.save(inv_b)

        alice = store.for_customer("alice")
        bob = store.for_customer("bob")

        assert len(alice.list_invoices()) == 1
        assert len(bob.list_invoices()) == 1
        assert alice.load_invoice(inv_a.invoice_id) is not None
        assert alice.load_invoice(inv_b.invoice_id) is None
        assert bob.load_invoice(inv_b.invoice_id) is not None
        assert bob.load_invoice(inv_a.invoice_id) is None

    def test_boundary_survives_reopen(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        inv = Invoice(customer_id="alice")
        inv.add_line_item("X", Decimal("100.00"))
        inv.issue()
        store.save(inv)
        del store

        reopened = SqliteInvoiceStore(db_path)
        alice = reopened.for_customer("alice")
        invoices = alice.list_invoices()
        assert len(invoices) == 1
        assert invoices[0].customer_id == "alice"

    def test_customer_access_value(self, db_path: str) -> None:
        store = SqliteInvoiceStore(db_path)
        inv = Invoice(customer_id="alice")
        store.save(inv)

        access = CustomerAccess("alice")
        boundary = CustomerBoundary(store, access)
        assert boundary.customer_id == "alice"
