"""Finance, treasury, spend-control, procurement, and collections kernels."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable, Mapping


@dataclass(frozen=True)
class CashPeriod:
    label: str
    receipts: Decimal
    disbursements: Decimal
    downside_receipt_factor: float = 1.0
    downside_disbursement_factor: float = 1.0

    def __post_init__(self) -> None:
        if self.receipts < 0 or self.disbursements < 0:
            raise ValueError("cash flows must be nonnegative magnitudes")
        if not 0 <= self.downside_receipt_factor <= 1:
            raise ValueError("downside_receipt_factor must be between 0 and 1")
        if self.downside_disbursement_factor < 1:
            raise ValueError("downside_disbursement_factor must be at least 1")


@dataclass(frozen=True)
class CashForecastRow:
    label: str
    opening_cash: Decimal
    receipts: Decimal
    disbursements: Decimal
    ending_cash: Decimal
    downside_ending_cash: Decimal


def rolling_cash_forecast(opening_cash: Decimal, periods: Iterable[CashPeriod]) -> tuple[CashForecastRow, ...]:
    if opening_cash < 0:
        raise ValueError("opening_cash must be nonnegative")
    base_cash = opening_cash
    downside_cash = opening_cash
    rows: list[CashForecastRow] = []
    for period in periods:
        next_base = base_cash + period.receipts - period.disbursements
        next_downside = (
            downside_cash
            + period.receipts * Decimal(str(period.downside_receipt_factor))
            - period.disbursements * Decimal(str(period.downside_disbursement_factor))
        )
        rows.append(CashForecastRow(
            period.label,
            base_cash,
            period.receipts,
            period.disbursements,
            next_base,
            next_downside,
        ))
        base_cash, downside_cash = next_base, next_downside
    return tuple(rows)


@dataclass(frozen=True)
class CloseTask:
    task_id: str
    owner: str
    status: str
    due_at: datetime
    completed_at: datetime | None = None
    blocker: str = ""
    control_id: str = ""


def close_control(tasks: Iterable[CloseTask], *, as_of: datetime) -> Mapping[str, object]:
    items = list(tasks)
    allowed = {"not_started", "in_progress", "blocked", "complete", "waived"}
    if any(item.status not in allowed for item in items):
        raise ValueError("unknown close-task status")
    completed = [item for item in items if item.status in {"complete", "waived"}]
    overdue = [
        item.task_id for item in items
        if item.status not in {"complete", "waived"} and item.due_at < as_of
    ]
    blockers = [item.task_id for item in items if item.status == "blocked" or item.blocker]
    missing_controls = [item.task_id for item in items if not item.control_id]
    completion_times = [
        (item.completed_at - item.due_at).total_seconds() / 86400
        for item in completed
        if item.completed_at is not None
    ]
    return {
        "task_count": len(items),
        "completion_rate": len(completed) / len(items) if items else 0.0,
        "overdue_task_ids": tuple(sorted(overdue)),
        "blocked_task_ids": tuple(sorted(blockers)),
        "missing_control_task_ids": tuple(sorted(missing_controls)),
        "average_days_vs_due": sum(completion_times) / len(completion_times) if completion_times else 0.0,
        "ready_to_close": bool(items) and len(completed) == len(items) and not missing_controls,
    }


@dataclass(frozen=True)
class SpendRequest:
    request_id: str
    category: str
    amount: Decimal
    requester: str
    vendor_id: str
    budget_remaining: Decimal
    contract_id: str = ""


@dataclass(frozen=True)
class SpendPolicy:
    category_limits: Mapping[str, Decimal]
    approval_threshold: Decimal
    contract_required_threshold: Decimal
    blocked_vendors: frozenset[str] = frozenset()


@dataclass(frozen=True)
class SpendDecision:
    request_id: str
    status: str
    reasons: tuple[str, ...]


def decide_spend(request: SpendRequest, policy: SpendPolicy) -> SpendDecision:
    if request.amount <= 0:
        raise ValueError("spend amount must be positive")
    reasons: list[str] = []
    if request.category not in policy.category_limits:
        reasons.append("unknown_category")
    elif request.amount > policy.category_limits[request.category]:
        reasons.append("category_limit_exceeded")
    if request.amount > request.budget_remaining:
        reasons.append("budget_exceeded")
    if request.vendor_id in policy.blocked_vendors:
        reasons.append("blocked_vendor")
    if request.amount >= policy.contract_required_threshold and not request.contract_id:
        reasons.append("contract_required")
    hard_reject = {"unknown_category", "budget_exceeded", "blocked_vendor"}.intersection(reasons)
    if hard_reject:
        status = "rejected"
    elif reasons or request.amount >= policy.approval_threshold:
        if request.amount >= policy.approval_threshold:
            reasons.append("approval_threshold")
        status = "approval_required"
    else:
        status = "approved"
    return SpendDecision(request.request_id, status, tuple(sorted(set(reasons))))


@dataclass(frozen=True)
class SupplierContract:
    contract_id: str
    unit_prices: Mapping[str, Decimal]
    quantity_tolerance: float = 0.0
    tax_rate: float = 0.0
    early_payment_discount: float = 0.0

    def __post_init__(self) -> None:
        for name in ("quantity_tolerance", "tax_rate", "early_payment_discount"):
            value = getattr(self, name)
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class PurchaseOrder:
    po_id: str
    contract_id: str
    quantities: Mapping[str, int]


@dataclass(frozen=True)
class Invoice:
    invoice_id: str
    po_id: str
    quantities: Mapping[str, int]
    unit_prices: Mapping[str, Decimal]
    subtotal: Decimal
    tax: Decimal
    discount_taken: Decimal = Decimal("0")


@dataclass(frozen=True)
class InvoiceAudit:
    invoice_id: str
    expected_subtotal: Decimal
    expected_tax: Decimal
    expected_discount: Decimal
    stated_total: Decimal
    expected_total: Decimal
    leakage: Decimal
    exceptions: tuple[str, ...]


def audit_invoice(
    invoice: Invoice,
    purchase_order: PurchaseOrder,
    contract: SupplierContract,
    *,
    prior_invoice_ids: Iterable[str] = (),
) -> InvoiceAudit:
    exceptions: list[str] = []
    if invoice.invoice_id in set(prior_invoice_ids):
        exceptions.append("duplicate_invoice")
    if invoice.po_id != purchase_order.po_id:
        exceptions.append("purchase_order_mismatch")
    if purchase_order.contract_id != contract.contract_id:
        exceptions.append("contract_mismatch")
    expected_subtotal = Decimal("0")
    for sku, invoiced_quantity in invoice.quantities.items():
        ordered_quantity = purchase_order.quantities.get(sku, 0)
        maximum_quantity = ordered_quantity * (1 + contract.quantity_tolerance)
        if invoiced_quantity < 0 or invoiced_quantity > maximum_quantity + 1e-9:
            exceptions.append(f"quantity_exception:{sku}")
        contract_price = contract.unit_prices.get(sku)
        if contract_price is None:
            exceptions.append(f"uncontracted_sku:{sku}")
            continue
        invoiced_price = invoice.unit_prices.get(sku)
        if invoiced_price != contract_price:
            exceptions.append(f"price_exception:{sku}")
        expected_subtotal += contract_price * invoiced_quantity
    expected_tax = expected_subtotal * Decimal(str(contract.tax_rate))
    expected_discount = expected_subtotal * Decimal(str(contract.early_payment_discount))
    stated_total = invoice.subtotal + invoice.tax - invoice.discount_taken
    expected_total = expected_subtotal + expected_tax - expected_discount
    if invoice.subtotal != sum(
        (invoice.unit_prices.get(sku, Decimal("0")) * quantity for sku, quantity in invoice.quantities.items()),
        Decimal("0"),
    ):
        exceptions.append("invoice_math_error")
    if invoice.tax != expected_tax:
        exceptions.append("tax_exception")
    if invoice.discount_taken < expected_discount:
        exceptions.append("missed_discount")
    leakage = max(stated_total - expected_total, Decimal("0"))
    return InvoiceAudit(
        invoice.invoice_id,
        expected_subtotal,
        expected_tax,
        expected_discount,
        stated_total,
        expected_total,
        leakage,
        tuple(sorted(set(exceptions))),
    )


@dataclass(frozen=True)
class Receivable:
    invoice_id: str
    customer_id: str
    amount: Decimal
    due_date: date
    dispute: bool = False
    customer_risk: float = 0.0


def prioritize_collections(receivables: Iterable[Receivable], *, as_of: date) -> tuple[tuple[str, float], ...]:
    ranked = []
    for item in receivables:
        if item.amount < 0 or not 0 <= item.customer_risk <= 1:
            raise ValueError("invalid receivable")
        days_past_due = max((as_of - item.due_date).days, 0)
        score = float(item.amount) * (1 + min(days_past_due, 180) / 180) * (1 + item.customer_risk)
        if item.dispute:
            score *= 1.25
        ranked.append((item.invoice_id, score))
    return tuple(sorted(ranked, key=lambda item: (-item[1], item[0])))
