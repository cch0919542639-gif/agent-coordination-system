"""Durable smoke tests: multi-customer isolation + reopen behavior."""

import os
import tempfile
from decimal import Decimal

import pytest

from src.billing.generation import InvoiceGenerationRequest, InvoiceGenerator
from src.billing.payment import PaymentRecorder
from src.billing.persistence import InvoiceStoreProtocol
from src.billing.queries import BalanceQuery
from src.billing.sqlite_store import SqliteInvoiceStore


@pytest.fixture
def db_path() -> str:
    tmp = tempfile.mktemp(suffix=".db")
    yield tmp
    try:
        os.remove(tmp)
    except PermissionError:
        pass


class TestDurableMultiCustomerSmoke:
    def test_customer_isolation_survives_reopen(self, db_path: str) -> None:
        store: InvoiceStoreProtocol = SqliteInvoiceStore(db_path)
        generator = InvoiceGenerator(store)
        recorder = PaymentRecorder(store)
        query = BalanceQuery(store)

        inv_a = generator.generate(
            InvoiceGenerationRequest(
                customer_id="alice",
                line_items=[{"description": "Consulting", "amount": "2000.00"}],
            )
        )
        inv_b = generator.generate(
            InvoiceGenerationRequest(
                customer_id="bob",
                line_items=[{"description": "Setup", "amount": "500.00"}],
            )
        )

        recorder.record_payment(inv_a.invoice_id, Decimal("800.00"))
        recorder.record_payment(inv_b.invoice_id, Decimal("500.00"))

        result_a = query.query(inv_a.invoice_id)
        result_b = query.query(inv_b.invoice_id)
        assert result_a.balance == Decimal("1200.00")
        assert result_a.status == "issued"
        assert result_b.balance == Decimal("0")
        assert result_b.status == "paid"

        del store, generator, recorder, query

        reopened: InvoiceStoreProtocol = SqliteInvoiceStore(db_path)
        query2 = BalanceQuery(reopened)
        list_a = reopened.list_by_customer("alice")
        list_b = reopened.list_by_customer("bob")

        assert len(list_a) == 1
        assert len(list_b) == 1
        assert list_a[0].balance == Decimal("1200.00")
        assert list_b[0].balance == Decimal("0")
        assert list_b[0].status.value == "paid"

        result_a2 = query2.query(inv_a.invoice_id)
        result_b2 = query2.query(inv_b.invoice_id)
        assert result_a2.balance == Decimal("1200.00")
        assert result_b2.balance == Decimal("0")

    def test_multi_invoice_per_customer_after_reopen(self, db_path: str) -> None:
        store: InvoiceStoreProtocol = SqliteInvoiceStore(db_path)
        generator = InvoiceGenerator(store)
        recorder = PaymentRecorder(store)

        invoices = []
        for i in range(3):
            inv = generator.generate(
                InvoiceGenerationRequest(
                    customer_id="alice",
                    line_items=[
                        {"description": f"Item {i+1}", "amount": "100.00"}
                    ],
                )
            )
            invoices.append(inv)

        recorder.record_payment(invoices[0].invoice_id, Decimal("100.00"))
        recorder.record_payment(invoices[1].invoice_id, Decimal("50.00"))

        assert store.count() == 3
        assert len(store.list_by_customer("alice")) == 3
        assert store.list_by_customer("bob") == []

        del store, generator, recorder

        reopened: InvoiceStoreProtocol = SqliteInvoiceStore(db_path)
        assert reopened.count() == 3
        alice_invoices = reopened.list_by_customer("alice")
        assert len(alice_invoices) == 3

        loaded_0 = reopened.load(invoices[0].invoice_id)
        loaded_1 = reopened.load(invoices[1].invoice_id)
        loaded_2 = reopened.load(invoices[2].invoice_id)
        assert loaded_0 is not None
        assert loaded_1 is not None
        assert loaded_2 is not None
        assert loaded_0.balance == Decimal("0")
        assert loaded_0.status.value == "paid"
        assert loaded_1.balance == Decimal("50.00")
        assert loaded_1.status.value == "issued"
        assert loaded_2.balance == Decimal("100.00")
        assert loaded_2.status.value == "issued"
