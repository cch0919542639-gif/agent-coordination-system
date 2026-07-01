"""Tests proving billing services work with the durable SqliteInvoiceStore."""

import os
import tempfile
from decimal import Decimal

import pytest

from src.billing.generation import InvoiceGenerationRequest, InvoiceGenerator
from src.billing.models import InvoiceStatus
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


@pytest.fixture
def store(db_path: str) -> SqliteInvoiceStore:
    return SqliteInvoiceStore(db_path)


class TestProtocolConformance:
    def test_sqlite_store_satisfies_protocol(self, store: SqliteInvoiceStore) -> None:
        assert isinstance(store, InvoiceStoreProtocol)

    def test_in_memory_store_satisfies_protocol(self) -> None:
        from src.billing.persistence import InvoiceStore

        assert isinstance(InvoiceStore(), InvoiceStoreProtocol)


class TestGenerateWithDurableStore:
    def test_generate_and_load(self, store: SqliteInvoiceStore) -> None:
        generator = InvoiceGenerator(store)
        request = InvoiceGenerationRequest(
            customer_id="durable-cust-001",
            line_items=[
                {"description": "Consulting", "amount": "1200.00"},
                {"description": "License", "amount": "300.00"},
            ],
        )

        invoice = generator.generate(request)

        assert invoice.customer_id == "durable-cust-001"
        assert invoice.total == Decimal("1500.00")
        assert invoice.status == InvoiceStatus.ISSUED

        loaded = store.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.total == Decimal("1500.00")
        assert loaded.status == InvoiceStatus.ISSUED

    def test_generate_persists_across_store_instances(self, db_path: str) -> None:
        store1 = SqliteInvoiceStore(db_path)
        generator = InvoiceGenerator(store1)
        request = InvoiceGenerationRequest(
            customer_id="durable-cust-002",
            line_items=[{"description": "Service", "amount": "500.00"}],
        )
        invoice = generator.generate(request)

        del store1

        store2 = SqliteInvoiceStore(db_path)
        loaded = store2.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.customer_id == "durable-cust-002"
        assert loaded.total == Decimal("500.00")


class TestPaymentWithDurableStore:
    def test_partial_payment(self, store: SqliteInvoiceStore) -> None:
        generator = InvoiceGenerator(store)
        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="pay-cust-001",
                line_items=[{"description": "Service", "amount": "1000.00"}],
            )
        )

        recorder = PaymentRecorder(store)
        updated = recorder.record_payment(invoice.invoice_id, Decimal("400.00"))

        assert updated.paid_amount == Decimal("400.00")
        assert updated.balance == Decimal("600.00")
        assert updated.status == InvoiceStatus.ISSUED

    def test_full_payment(self, store: SqliteInvoiceStore) -> None:
        generator = InvoiceGenerator(store)
        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="pay-cust-002",
                line_items=[{"description": "Service", "amount": "750.00"}],
            )
        )

        recorder = PaymentRecorder(store)
        updated = recorder.record_payment(invoice.invoice_id, Decimal("750.00"))

        assert updated.paid_amount == Decimal("750.00")
        assert updated.balance == Decimal("0")
        assert updated.status == InvoiceStatus.PAID

    def test_payment_persists_across_reopen(self, db_path: str) -> None:
        store1 = SqliteInvoiceStore(db_path)
        generator = InvoiceGenerator(store1)
        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="pay-cust-003",
                line_items=[{"description": "Service", "amount": "1000.00"}],
            )
        )

        recorder = PaymentRecorder(store1)
        recorder.record_payment(invoice.invoice_id, Decimal("400.00"))
        del store1

        store2 = SqliteInvoiceStore(db_path)
        loaded = store2.load(invoice.invoice_id)
        assert loaded is not None
        assert loaded.paid_amount == Decimal("400.00")
        assert loaded.balance == Decimal("600.00")


class TestQueryWithDurableStore:
    def test_query_unpaid(self, store: SqliteInvoiceStore) -> None:
        generator = InvoiceGenerator(store)
        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="query-cust-001",
                line_items=[{"description": "Service", "amount": "2000.00"}],
            )
        )

        query = BalanceQuery(store)
        result = query.query(invoice.invoice_id)

        assert result.total == Decimal("2000.00")
        assert result.paid_amount == Decimal("0")
        assert result.balance == Decimal("2000.00")
        assert result.status == "issued"

    def test_query_after_payment(self, store: SqliteInvoiceStore) -> None:
        generator = InvoiceGenerator(store)
        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="query-cust-002",
                line_items=[{"description": "Service", "amount": "2000.00"}],
            )
        )

        recorder = PaymentRecorder(store)
        recorder.record_payment(invoice.invoice_id, Decimal("1500.00"))

        query = BalanceQuery(store)
        result = query.query(invoice.invoice_id)

        assert result.total == Decimal("2000.00")
        assert result.paid_amount == Decimal("1500.00")
        assert result.balance == Decimal("500.00")
        assert result.status == "issued"


class TestFullServicePathWithDurableStore:
    """End-to-end: generate -> pay -> query, all through durable store."""

    def test_generate_pay_query_partial(self, store: SqliteInvoiceStore) -> None:
        generator = InvoiceGenerator(store)
        recorder = PaymentRecorder(store)
        query = BalanceQuery(store)

        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="e2e-customer",
                line_items=[
                    {"description": "Consulting", "amount": "2000.00"},
                    {"description": "License", "amount": "500.00"},
                ],
            )
        )
        assert invoice.total == Decimal("2500.00")

        updated = recorder.record_payment(invoice.invoice_id, Decimal("1000.00"))
        assert updated.paid_amount == Decimal("1000.00")
        assert updated.balance == Decimal("1500.00")

        result = query.query(invoice.invoice_id)
        assert result.invoice_id == invoice.invoice_id
        assert result.customer_id == "e2e-customer"
        assert result.total == Decimal("2500.00")
        assert result.paid_amount == Decimal("1000.00")
        assert result.balance == Decimal("1500.00")
        assert result.status == "issued"

    def test_generate_pay_query_full(self, store: SqliteInvoiceStore) -> None:
        generator = InvoiceGenerator(store)
        recorder = PaymentRecorder(store)
        query = BalanceQuery(store)

        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="e2e-customer",
                line_items=[{"description": "Service", "amount": "750.00"}],
            )
        )

        updated = recorder.record_payment(invoice.invoice_id, Decimal("750.00"))
        assert updated.paid_amount == Decimal("750.00")
        assert updated.balance == Decimal("0")
        assert updated.status == InvoiceStatus.PAID

        result = query.query(invoice.invoice_id)
        assert result.total == Decimal("750.00")
        assert result.paid_amount == Decimal("750.00")
        assert result.balance == Decimal("0")
        assert result.status == "paid"

    def test_survives_process_restart(self, db_path: str) -> None:
        store1 = SqliteInvoiceStore(db_path)
        generator = InvoiceGenerator(store1)
        recorder = PaymentRecorder(store1)

        invoice = generator.generate(
            InvoiceGenerationRequest(
                customer_id="restart-customer",
                line_items=[{"description": "Service", "amount": "1200.00"}],
            )
        )
        recorder.record_payment(invoice.invoice_id, Decimal("800.00"))
        del store1

        store2 = SqliteInvoiceStore(db_path)
        query = BalanceQuery(store2)
        result = query.query(invoice.invoice_id)

        assert result.total == Decimal("1200.00")
        assert result.paid_amount == Decimal("800.00")
        assert result.balance == Decimal("400.00")
        assert result.status == "issued"
