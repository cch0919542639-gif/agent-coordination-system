from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Iterator, List, Optional

from src.billing.access import CustomerAccess, CustomerBoundary
from src.billing.models import Invoice, InvoiceLineItem, InvoiceStatus


SCHEMA_VERSION = 1
WRITE_LOCK_TIMEOUT = 10.0


class SchemaVersionError(Exception):
    pass


class WriteContentionError(Exception):
    pass


class SqliteInvoiceStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 3000")
        return conn

    def _execute(self, sql: str, params=()):
        with closing(self._conn()) as conn:
            return conn.execute(sql, params)

    @contextmanager
    def _write_guard(self) -> Iterator[None]:
        if not self._lock.acquire(timeout=WRITE_LOCK_TIMEOUT):
            raise WriteContentionError(
                f"Could not acquire write lock within {WRITE_LOCK_TIMEOUT}s"
            )
        try:
            yield
        finally:
            self._lock.release()

    @property
    def concurrency_model(self) -> str:
        return "single-process, serialized-writes"

    def _init_db(self) -> None:
        with closing(self._conn()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS _schema_version (
                    key   TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                )
                """
            )
            cursor = conn.execute(
                "SELECT value FROM _schema_version WHERE key = 'schema_version'"
            )
            row = cursor.fetchone()
            current = row["value"] if row else 0

            for version in range(current + 1, SCHEMA_VERSION + 1):
                getattr(self, f"_migration_v{version}")()
                conn.execute(
                    "INSERT OR REPLACE INTO _schema_version (key, value) VALUES ('schema_version', ?)",
                    (version,),
                )

            conn.commit()

    def _migration_v1(self) -> None:
        self._execute(
            """
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id   TEXT PRIMARY KEY,
                customer_id  TEXT NOT NULL,
                status       TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                paid_amount  TEXT NOT NULL,
                line_items   TEXT NOT NULL
            )
            """
        )

    @property
    def schema_version(self) -> int:
        with closing(self._conn()) as conn:
            cursor = conn.execute(
                "SELECT value FROM _schema_version WHERE key = 'schema_version'"
            )
            row = cursor.fetchone()
        return row["value"] if row else 0

    def _row_to_invoice(self, row: sqlite3.Row) -> Invoice:
        line_items_data = json.loads(row["line_items"])
        line_items = [
            InvoiceLineItem(
                description=item["description"],
                amount=Decimal(item["amount"]),
            )
            for item in line_items_data
        ]
        return Invoice(
            invoice_id=row["invoice_id"],
            customer_id=row["customer_id"],
            status=InvoiceStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            paid_amount=Decimal(row["paid_amount"]),
            line_items=line_items,
        )

    def _invoice_to_row(self, invoice: Invoice) -> Dict[str, str]:
        return {
            "invoice_id": invoice.invoice_id,
            "customer_id": invoice.customer_id,
            "status": invoice.status.value,
            "created_at": invoice.created_at.isoformat(),
            "paid_amount": str(invoice.paid_amount),
            "line_items": json.dumps(
                [
                    {"description": item.description, "amount": str(item.amount)}
                    for item in invoice.line_items
                ]
            ),
        }

    def save(self, invoice: Invoice) -> None:
        with self._write_guard():
            row = self._invoice_to_row(invoice)
            with closing(self._conn()) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO invoices
                        (invoice_id, customer_id, status, created_at, paid_amount, line_items)
                    VALUES
                        (:invoice_id, :customer_id, :status, :created_at, :paid_amount, :line_items)
                    """,
                    row,
                )
                conn.commit()

    def load(self, invoice_id: str) -> Optional[Invoice]:
        with closing(self._conn()) as conn:
            cursor = conn.execute(
                "SELECT * FROM invoices WHERE invoice_id = ?", (invoice_id,)
            )
            row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_invoice(row)

    def delete(self, invoice_id: str) -> None:
        with self._write_guard():
            with closing(self._conn()) as conn:
                conn.execute(
                    "DELETE FROM invoices WHERE invoice_id = ?", (invoice_id,)
                )
                conn.commit()

    def list_by_customer(self, customer_id: str) -> List[Invoice]:
        with closing(self._conn()) as conn:
            cursor = conn.execute(
                "SELECT * FROM invoices WHERE customer_id = ?", (customer_id,)
            )
            rows = cursor.fetchall()
        return [self._row_to_invoice(row) for row in rows]

    def count(self) -> int:
        with closing(self._conn()) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM invoices")
            row = cursor.fetchone()
        return row[0] if row else 0

    def for_customer(self, customer_id: str) -> CustomerBoundary:
        return CustomerBoundary(self, CustomerAccess(customer_id))
