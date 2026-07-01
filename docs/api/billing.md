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

### Known Remaining Limits

- `SqliteInvoiceStore` uses the built-in `sqlite3` module and serializes via JSON — no migration mechanism exists yet for schema evolution
- Concurrency is local-only — no distributed locking or multi-process write safety is tested
- Customer isolation relies on `list_by_customer()` filtering by `customer_id` string — no ownership or access-control layer exists
- No third-party gateway integration (out of scope per phase intake)
