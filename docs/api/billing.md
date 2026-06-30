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

The `InvoiceStore` class provides in-memory persistence for invoices.

### Methods

| Method | Signature | Description |
|---|---|---|
| `save` | `(invoice: Invoice) -> None` | Store an invoice (insert or update) |
| `load` | `(invoice_id: str) -> Optional[Invoice]` | Load an invoice by ID |
| `delete` | `(invoice_id: str) -> None` | Remove an invoice from the store |
| `list_by_customer` | `(customer_id: str) -> list[Invoice]` | List all invoices for a customer |
| `count` | `() -> int` | Total number of stored invoices |

## Usage Example

```python
from decimal import Decimal
from src.billing.models import Invoice
from src.billing.persistence import InvoiceStore

store = InvoiceStore()

invoice = Invoice(customer_id="alice")
invoice.add_line_item("Consulting", Decimal("1200.00"))
invoice.add_line_item("License", Decimal("300.00"))
invoice.issue()

store.save(invoice)

loaded = store.load(invoice.invoice_id)
loaded.record_payment(Decimal("500.00"))
print(loaded.balance)  # 1000.00
```
