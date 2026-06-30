from decimal import Decimal

import pytest

from src.billing.models import Invoice, InvoiceLineItem, InvoiceStatus


class TestInvoiceLineItem:
    def test_create_valid_line_item(self) -> None:
        item = InvoiceLineItem(description="Setup fee", amount=Decimal("100.00"))
        assert item.description == "Setup fee"
        assert item.amount == Decimal("100.00")

    def test_zero_amount_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            InvoiceLineItem(description="Free item", amount=Decimal("0"))

    def test_negative_amount_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            InvoiceLineItem(description="Bad item", amount=Decimal("-50"))


class TestInvoice:
    def test_create_draft_invoice(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        assert invoice.status == InvoiceStatus.DRAFT
        assert invoice.total == Decimal("0")
        assert invoice.balance == Decimal("0")
        assert invoice.paid_amount == Decimal("0")

    def test_add_line_item(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Consulting", Decimal("500.00"))
        invoice.add_line_item("Hosting", Decimal("99.99"))
        assert len(invoice.line_items) == 2
        assert invoice.total == Decimal("599.99")
        assert invoice.balance == Decimal("599.99")

    def test_issue_invoice(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Setup", Decimal("250.00"))
        invoice.issue()
        assert invoice.status == InvoiceStatus.ISSUED

    def test_issue_empty_invoice_raises(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        with pytest.raises(ValueError, match="no line items"):
            invoice.issue()

    def test_issue_draft_only(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Test", Decimal("10"))
        invoice.issue()
        with pytest.raises(ValueError, match="Only draft"):
            invoice.issue()

    def test_record_payment(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Service", Decimal("1000.00"))
        invoice.issue()
        invoice.record_payment(Decimal("400.00"))
        assert invoice.paid_amount == Decimal("400.00")
        assert invoice.balance == Decimal("600.00")
        assert invoice.status == InvoiceStatus.ISSUED

    def test_full_payment_marks_paid(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Service", Decimal("500.00"))
        invoice.issue()
        invoice.record_payment(Decimal("500.00"))
        assert invoice.status == InvoiceStatus.PAID
        assert invoice.balance == Decimal("0")

    def test_overpayment_raises(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Item", Decimal("100.00"))
        invoice.issue()
        with pytest.raises(ValueError, match="exceeds"):
            invoice.record_payment(Decimal("200.00"))

    def test_cancel_draft(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        invoice.cancel()
        assert invoice.status == InvoiceStatus.CANCELLED

    def test_cancel_issued(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Item", Decimal("50"))
        invoice.issue()
        invoice.cancel()
        assert invoice.status == InvoiceStatus.CANCELLED

    def test_cancel_paid_raises(self) -> None:
        invoice = Invoice(customer_id="cust-001")
        invoice.add_line_item("Item", Decimal("50"))
        invoice.issue()
        invoice.record_payment(Decimal("50"))
        with pytest.raises(ValueError, match="paid or already"):
            invoice.cancel()
