from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import List


class InvoiceStatus(Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"


@dataclass
class InvoiceLineItem:
    description: str
    amount: Decimal

    def __post_init__(self) -> None:
        if self.amount <= Decimal("0"):
            raise ValueError("Line item amount must be positive")


@dataclass
class Invoice:
    customer_id: str
    line_items: List[InvoiceLineItem] = field(default_factory=list)
    status: InvoiceStatus = InvoiceStatus.DRAFT
    invoice_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    paid_amount: Decimal = Decimal("0")

    @property
    def total(self) -> Decimal:
        return sum((item.amount for item in self.line_items), Decimal("0"))

    @property
    def balance(self) -> Decimal:
        return self.total - self.paid_amount

    def add_line_item(self, description: str, amount: Decimal) -> None:
        if self.status != InvoiceStatus.DRAFT:
            raise ValueError("Cannot modify a non-draft invoice")
        self.line_items.append(InvoiceLineItem(description=description, amount=amount))

    def issue(self) -> None:
        if self.status != InvoiceStatus.DRAFT:
            raise ValueError("Only draft invoices can be issued")
        if not self.line_items:
            raise ValueError("Cannot issue an invoice with no line items")
        if self.total <= Decimal("0"):
            raise ValueError("Cannot issue an invoice with zero total")
        self.status = InvoiceStatus.ISSUED

    def record_payment(self, amount: Decimal) -> None:
        if self.status == InvoiceStatus.DRAFT:
            raise ValueError("Cannot pay a draft invoice")
        if self.status == InvoiceStatus.CANCELLED:
            raise ValueError("Cannot pay a cancelled invoice")
        if amount <= Decimal("0"):
            raise ValueError("Payment amount must be positive")
        new_paid = self.paid_amount + amount
        if new_paid > self.total:
            raise ValueError("Payment exceeds invoice total")
        self.paid_amount = new_paid
        if self.paid_amount == self.total:
            self.status = InvoiceStatus.PAID

    def cancel(self) -> None:
        if self.status in (InvoiceStatus.PAID, InvoiceStatus.CANCELLED):
            raise ValueError("Cannot cancel a paid or already cancelled invoice")
        self.status = InvoiceStatus.CANCELLED
