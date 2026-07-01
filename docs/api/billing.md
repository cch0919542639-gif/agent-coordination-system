# Billing API

## Invoice Model

The `Invoice` dataclass represents a single invoice in the billing system.

### Fields

| Field | Type | Description |
|---|---|---|
| `invoice_id` | `str` | Unique identifier (auto-generated hex string) |
| `customer_id` | `str` | Customer or account identifier |
| `line_items` | `list[InvoiceLineItem]` | Line items on the invoice |
| `status` | `InvoiceStatus` | Current status: `draft`, `issued`, `paid`, `cancelled` |
| `created_at` | `datetime` | UTC timestamp of creation |
| `paid_amount` | `Decimal` | Running total of payments recorded against this invoice |

### Computed Properties

- `total` — sum of all line item amounts
- `balance` — `total - paid_amount`

### InvoiceLineItem

| Field | Type | Description |
|---|---|---|
| `description` | `str` | Line item description |
| `amount` | `Decimal` | Positive monetary amount |

### Lifecycle

```
DRAFT -> ISSUED -> PAID
  |         |
  +---> CANCELLED
```

- An invoice starts in `DRAFT`. Line items may be added only while in draft.
- `issue()` transitions to `ISSUED`. The invoice must have at least one line item with a positive total.
- `record_payment(amount)` records a payment. Full payment transitions to `PAID`.
- `cancel()` transitions to `CANCELLED`. Paid or already-cancelled invoices may not be cancelled.

## Invoice Persistence

### Store Contract (InvoiceStoreProtocol)

All billing services depend on the `InvoiceStoreProtocol`, a structural protocol that defines the five methods any invoice store must provide:

| Method | Signature | Description |
|---|---|---|
| `save` | `(invoice: Invoice) -> None` | Store an invoice (insert or update) |
| `load` | `(invoice_id: str) -> Optional[Invoice]` | Load an invoice by ID |
| `delete` | `(invoice_id: str) -> None` | Remove an invoice from the store |
| `list_by_customer` | `(customer_id: str) -> list[Invoice]` | List all invoices for a customer |
| `count` | `() -> int` | Total number of stored invoices |

Services accept `InvoiceStoreProtocol` rather than a concrete store class, so they work transparently with any implementation that provides these methods. The protocol is `@runtime_checkable`, so `isinstance` checks work at runtime.

### In-Memory Store

The `InvoiceStore` class provides in-memory persistence for invoices. It satisfies `InvoiceStoreProtocol`.

### Methods

| Method | Signature | Description |
|---|---|---|
| `save` | `(invoice: Invoice) -> None` | Store an invoice (insert or update) |
| `load` | `(invoice_id: str) -> Optional[Invoice]` | Load an invoice by ID |
| `delete` | `(invoice_id: str) -> None` | Remove an invoice from the store |
| `list_by_customer` | `(customer_id: str) -> list[Invoice]` | List all invoices for a customer |
| `count` | `() -> int` | Total number of stored invoices |

### SQLite-Backed Store

The `SqliteInvoiceStore` class provides durable SQLite-backed persistence with the same interface as `InvoiceStore`.

Constructor: `SqliteInvoiceStore(db_path: str)` — accepts a filesystem path for the SQLite database file. Pass `":memory:"` for an in-memory SQLite database (useful for testing).

| Method | Signature | Description |
|---|---|---|
| `save` | `(invoice: Invoice) -> None` | Store an invoice (insert or update) |
| `load` | `(invoice_id: str) -> Optional[Invoice]` | Load an invoice by ID |
| `delete` | `(invoice_id: str) -> None` | Remove an invoice from the store |
| `list_by_customer` | `(customer_id: str) -> list[Invoice]` | List all invoices for a customer |
| `count` | `() -> int` | Total number of stored invoices |

| `schema_version` | `() -> int` | Current schema version of the database |
| `concurrency_model` | `() -> str` | Description of the supported concurrency model |

The `SCHEMA_VERSION` module constant (`sqlite_store.SCHEMA_VERSION`) defines the latest schema version. The store also exports `SchemaVersionError` for migration-related failures and `WriteContentionError` for write-lock timeouts.

The SQLite store serializes `Decimal` values as strings (preserving precision), `datetime` as ISO-8601 text, and line items as JSON. Data persisted to disk survives process restarts and store re-initialization.

## Invoice Generation Service

The `InvoiceGenerator` class provides a higher-level API for creating, issuing, and persisting invoices in a single step.

### InvoiceGenerationRequest

| Field | Type | Description |
|---|---|---|
| `customer_id` | `str` | Customer identifier (required, non-empty) |
| `line_items` | `list[dict]` | List of item dicts with `description` and `amount` keys |

Each line item dict must contain:
- `description` (str) — item description
- `amount` (str or Decimal) — positive monetary amount

### InvoiceGenerator

| Method | Signature | Description |
|---|---|---|
| `generate` | `(request: InvoiceGenerationRequest) -> Invoice` | Validate, create, issue, persist, and return invoice |

### Errors

`InvoiceGenerationError` is raised when:
- `customer_id` is empty or missing
- `line_items` is empty
- Any line item has an invalid amount (delegated to `InvoiceLineItem` validation)

### Usage Example

```python
from decimal import Decimal
from src.billing.generation import InvoiceGenerationRequest, InvoiceGenerator
from src.billing.models import Invoice
from src.billing.persistence import InvoiceStore

store = InvoiceStore()
generator = InvoiceGenerator(store)

request = InvoiceGenerationRequest(
    customer_id="alice",
    line_items=[
        {"description": "Consulting", "amount": "1200.00"},
        {"description": "License", "amount": "300.00"},
    ],
)

invoice = generator.generate(request)
print(invoice.total)    # 1500.00
print(invoice.status)   # issued

loaded = store.load(invoice.invoice_id)
loaded.record_payment(Decimal("500.00"))
print(loaded.balance)  # 1000.00
```

## Payment Recording Service

The `PaymentRecorder` class provides a higher-level API for recording payments against issued invoices and persisting the updated state.

### PaymentRecorder

| Method | Signature | Description |
|---|---|---|
| `record_payment` | `(invoice_id: str, amount: Decimal) -> Invoice` | Load invoice, record payment, save, return updated invoice |

### Errors

`PaymentRecordError` is raised when:
- The invoice ID does not exist in the store
- The invoice is in `DRAFT` state (must be issued first)
- The invoice is `CANCELLED`
- The payment amount is zero or negative
- The payment exceeds the remaining balance

### Usage Example

```python
from decimal import Decimal
from src.billing.generation import InvoiceGenerationRequest, InvoiceGenerator
from src.billing.payment import PaymentRecorder
from src.billing.persistence import InvoiceStore

store = InvoiceStore()
generator = InvoiceGenerator(store)
recorder = PaymentRecorder(store)

invoice = generator.generate(InvoiceGenerationRequest(
    customer_id="alice",
    line_items=[{"description": "Consulting", "amount": "1200.00"}],
))

updated = recorder.record_payment(invoice.invoice_id, Decimal("500.00"))
print(updated.paid_amount)  # 500.00
print(updated.balance)      # 700.00
print(updated.status)       # issued
```

## Balance Query Service

The `BalanceQuery` class provides a read-only query path for invoice balance and state information.

### BalanceResult

| Field | Type | Description |
|---|---|---|
| `invoice_id` | `str` | Invoice identifier |
| `customer_id` | `str` | Customer identifier |
| `total` | `Decimal` | Sum of all line item amounts |
| `paid_amount` | `Decimal` | Total payments recorded |
| `balance` | `Decimal` | Remaining balance (`total - paid_amount`) |
| `status` | `str` | Invoice status (`draft`, `issued`, `paid`, `cancelled`) |
| `created_at` | `datetime` | UTC timestamp of invoice creation |

### BalanceQuery

| Method | Signature | Description |
|---|---|---|
| `query` | `(invoice_id: str) -> BalanceResult` | Load invoice and return balance information |

### Errors

`BalanceQueryError` is raised when the invoice ID does not exist in the store.

### Usage Example

```python
from decimal import Decimal
from src.billing.generation import InvoiceGenerationRequest, InvoiceGenerator
from src.billing.payment import PaymentRecorder
from src.billing.queries import BalanceQuery
from src.billing.persistence import InvoiceStore

store = InvoiceStore()
generator = InvoiceGenerator(store)
recorder = PaymentRecorder(store)
query = BalanceQuery(store)

invoice = generator.generate(InvoiceGenerationRequest(
    customer_id="alice",
    line_items=[{"description": "Consulting", "amount": "1200.00"}],
))

recorder.record_payment(invoice.invoice_id, Decimal("500.00"))

result = query.query(invoice.invoice_id)
print(result.total)        # 1200.00
print(result.paid_amount)  # 500.00
print(result.balance)      # 700.00
print(result.status)       # issued
```

## Integration Smoke Test

The `tests/billing/test_smoke.py` module validates the billing flow end-to-end:

1. **Generate invoice** — `InvoiceGenerator` creates an issued invoice with line items
2. **Record payment** — `PaymentRecorder` records a partial or full payment against the invoice
3. **Query balance** — `BalanceQuery` returns the updated balance and state

Two smoke paths are covered:
- **Partial payment** — 2-item invoice, partial payment recorded, balance reflects remaining amount (`issued` status preserved)
- **Full payment** — single-item invoice, full payment recorded, balance reaches zero (`paid` status)

### Validation Notes

```text
python -m pytest tests/billing/test_smoke.py -v
```

Expected output: 2 passed, confirming the three services interact correctly through the shared `InvoiceStore`.

The same smoke paths are also validated against the durable `SqliteInvoiceStore` in `tests/billing/test_durable_store_services.py`, confirming that `InvoiceGenerator`, `PaymentRecorder`, and `BalanceQuery` work identically with both store implementations via the `InvoiceStoreProtocol`.

## Durable Multi-Customer Smoke Test

The `tests/billing/test_durable_smoke.py` module extends coverage to multi-customer and multi-invoice scenarios under durable storage.

### Customer Isolation

Invoices for different customers are stored and queried independently via `SqliteInvoiceStore.list_by_customer()`. After recording payments, each customer's balance and status are unaffected by other customers' activity. This isolation survives store close and reopen.

### Multi-Invoice Listing

A single customer with multiple invoices is correctly enumerated by `list_by_customer()` and `count()` before and after store re-initialization. Individual invoice balances are preserved across reopen.

### Validation Notes

```text
python -m pytest tests/billing/test_durable_smoke.py -v
```

Expected output: 2 passed, confirming customer isolation and multi-invoice durability.

### Schema Versioning & Migration

`SqliteInvoiceStore` includes a built-in schema versioning and migration baseline. On every store initialization, it checks the version stored in the `_schema_version` system table and runs any pending migrations to bring the database up to `SCHEMA_VERSION` (`=1` as of this writing).

- **Fresh databases** — all migrations are applied in order, establishing the initial schema.
- **Existing databases** — only new migrations (versions > current) are applied; already-applied migrations are skipped.
- **Migration v1** — creates the `invoices` table (idempotent via `CREATE TABLE IF NOT EXISTS`), so existing databases created before schema versioning was introduced are automatically upgraded without data loss.

```python
from src.billing.sqlite_store import SqliteInvoiceStore, SCHEMA_VERSION

store = SqliteInvoiceStore("/path/to/billing.db")
print(store.schema_version)  # 1
print(SCHEMA_VERSION)        # 1
```

To add a new migration, implement `_migration_v<N>()` on `SqliteInvoiceStore`, bump `SCHEMA_VERSION`, and the store will apply it automatically on next initialization.

### Local Concurrency Guardrails

`SqliteInvoiceStore` uses a **single-process, serialized-writes** concurrency model.

#### Supported Behavior

- Multiple reads (`load`, `list_by_customer`, `count`) can proceed concurrently from any number of threads within the same process — no lock is required for read operations.
- Write operations (`save`, `delete`) are serialized by a per-instance `threading.Lock`. Concurrent writes from different threads on the same store instance are queued automatically.
- Each SQLite connection sets `PRAGMA busy_timeout = 3000`, so if another process holds a write lock on the database file, the connection waits up to 3 seconds before failing.
- `WriteContentionError` is raised if a write operation cannot acquire the in-process lock within `WRITE_LOCK_TIMEOUT` seconds (default: 10.0).

#### Unsupported Scenarios

- Multi-process writes to the same database file are not actively coordinated beyond SQLite's built-in file-level locking. Each process has its own in-process lock, so no cross-process serialization is guaranteed.
- Distributed or cluster-wide write coordination is out of scope.
- Read-after-write consistency across separate store instances pointing at the same file is best-effort (SQLite file locking applies).

```python
from src.billing.sqlite_store import SqliteInvoiceStore, WriteContentionError

store = SqliteInvoiceStore("/path/to/billing.db")
print(store.concurrency_model)  # "single-process, serialized-writes"
```

### Customer Access Boundary

The billing module provides an explicit access-boundary contract through `CustomerAccess` and `CustomerBoundary`. This boundary makes customer-scoped reads deliberate and auditable, without implementing authentication or authorization.

#### CustomerAccess

`CustomerAccess` is a frozen value object that represents "the caller has been verified to have access to this customer's data." It carries only a `customer_id` and is immutable.

```python
from src.billing.access import CustomerAccess

access = CustomerAccess("cust-001")
print(access.customer_id)  # "cust-001"
```

The billing layer **does not verify** that the caller is authorized to act as that customer. It trusts the `CustomerAccess` it receives. Outer layers (API gateways, auth middleware) are responsible for creating `CustomerAccess` after authenticating the caller and verifying authorization.

#### CustomerBoundary

`CustomerBoundary` wraps a store and a `CustomerAccess`, providing customer-scoped read methods that automatically filter by the customer ID.

| Method | Signature | Description |
|---|---|---|
| `list_invoices` | `() -> list[Invoice]` | List invoices for the boundary's customer |
| `load_invoice` | `(invoice_id: str) -> Optional[Invoice]` | Load invoice only if it belongs to this customer |
| `query_balance` | `(invoice_id: str) -> BalanceResult` | Query balance only if invoice belongs to this customer |

`load_invoice` returns `None` if the invoice does not exist or belongs to a different customer. `query_balance` raises `BalanceQueryError` if the invoice is not accessible.

```python
from src.billing.access import CustomerAccess, CustomerBoundary
from src.billing.persistence import InvoiceStore

store = InvoiceStore()
# ... save invoices ...

alice = CustomerBoundary(store, CustomerAccess("alice"))
for inv in alice.list_invoices():
    print(inv.invoice_id, inv.total)
```

#### Store Factory Method

Both `InvoiceStore` and `SqliteInvoiceStore` provide a `for_customer()` factory method that returns a `CustomerBoundary`:

```python
from src.billing.sqlite_store import SqliteInvoiceStore

store = SqliteInvoiceStore("/path/to/billing.db")
boundary = store.for_customer("alice")
print(boundary.customer_id)   # "alice"
print(boundary.list_invoices())
```

This method is part of `InvoiceStoreProtocol`, so all conforming stores support it.

#### Boundary Responsibility

| Layer | Responsibility |
|---|---|
| Billing (`CustomerBoundary`) | Enforces data-scoping — returns only invoices matching the `CustomerAccess.customer_id` |
| Outer layers (API, auth) | Enforces identity and authorization — creates `CustomerAccess` only after verifying the caller |

The billing module documents this split clearly: `CustomerBoundary` prevents accidental cross-customer data leaks within billing code, but it is not a security boundary. A caller that can construct an arbitrary `CustomerAccess("any-id")` can read any customer's data.

### Known Remaining Limits

- No third-party gateway integration (out of scope per phase intake)
