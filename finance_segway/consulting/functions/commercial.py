"""Commercial kernels: ICP scoring, sales telemetry, pricing, and GEO."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Iterable, Mapping


def _rate(value: float, name: str) -> float:
    result = float(value)
    if not 0 <= result <= 1:
        raise ValueError(f"{name} must be between 0 and 1")
    return result


@dataclass(frozen=True)
class Account:
    account_id: str
    features: Mapping[str, float]
    required_attributes: frozenset[str] = frozenset()


@dataclass(frozen=True)
class IdealCustomerProfile:
    feature_weights: Mapping[str, float]
    required_attributes: frozenset[str] = frozenset()
    minimum_score: float = 0.0


@dataclass(frozen=True)
class AccountScore:
    account_id: str
    score: float
    eligible: bool
    contributions: Mapping[str, float]
    missing_required: tuple[str, ...]


def score_accounts(accounts: Iterable[Account], profile: IdealCustomerProfile) -> tuple[AccountScore, ...]:
    if not profile.feature_weights or any(weight < 0 for weight in profile.feature_weights.values()):
        raise ValueError("ICP weights must be nonnegative and nonempty")
    total_weight = sum(profile.feature_weights.values())
    if total_weight <= 0:
        raise ValueError("ICP weights must sum to a positive value")
    scores: list[AccountScore] = []
    for account in accounts:
        contributions: dict[str, float] = {}
        for feature, weight in profile.feature_weights.items():
            value = _rate(account.features.get(feature, 0.0), feature)
            contributions[feature] = 100 * weight * value / total_weight
        missing = tuple(sorted(profile.required_attributes - account.required_attributes))
        score = sum(contributions.values())
        eligible = not missing and score >= profile.minimum_score
        scores.append(AccountScore(account.account_id, score, eligible, contributions, missing))
    return tuple(sorted(scores, key=lambda item: (-item.score, item.account_id)))


@dataclass(frozen=True)
class Lead:
    lead_id: str
    created_at: datetime
    first_response_at: datetime | None
    qualified: bool
    won: bool
    seller_hours: float


def sales_metrics(leads: Iterable[Lead], *, response_sla_minutes: float = 60.0) -> Mapping[str, float]:
    items = list(leads)
    if response_sla_minutes < 0:
        raise ValueError("response_sla_minutes must be nonnegative")
    response_minutes = []
    within_sla = 0
    for lead in items:
        if lead.seller_hours < 0:
            raise ValueError("seller_hours must be nonnegative")
        if lead.first_response_at is None:
            continue
        elapsed = (lead.first_response_at - lead.created_at).total_seconds() / 60
        if elapsed < 0:
            raise ValueError("first response cannot precede lead creation")
        response_minutes.append(elapsed)
        within_sla += elapsed <= response_sla_minutes
    count = len(items)
    qualified = sum(item.qualified for item in items)
    wins = sum(item.won for item in items)
    return {
        "lead_count": float(count),
        "response_coverage": len(response_minutes) / count if count else 0.0,
        "median_response_minutes": median(response_minutes) if response_minutes else 0.0,
        "response_sla_attainment": within_sla / count if count else 0.0,
        "qualification_rate": qualified / count if count else 0.0,
        "win_rate": wins / qualified if qualified else 0.0,
        "seller_hours": sum(item.seller_hours for item in items),
    }


@dataclass(frozen=True)
class Product:
    sku: str
    list_price: Decimal
    unit_cost: Decimal
    available_units: int


@dataclass(frozen=True)
class QuoteRequest:
    quote_id: str
    quantities: Mapping[str, int]
    requested_discount: float = 0.0


@dataclass(frozen=True)
class PricingPolicy:
    max_discount: float
    min_gross_margin: float
    material_quote_value: Decimal

    def __post_init__(self) -> None:
        _rate(self.max_discount, "max_discount")
        _rate(self.min_gross_margin, "min_gross_margin")
        if self.material_quote_value < 0:
            raise ValueError("material_quote_value must be nonnegative")


@dataclass(frozen=True)
class QuoteLine:
    sku: str
    quantity: int
    unit_price: Decimal
    extended_price: Decimal
    gross_margin: float


@dataclass(frozen=True)
class Quote:
    quote_id: str
    lines: tuple[QuoteLine, ...]
    subtotal: Decimal
    requested_discount: float
    applied_discount: float
    total: Decimal
    approval_required: bool
    approval_reasons: tuple[str, ...]


def build_quote(
    request: QuoteRequest,
    products: Mapping[str, Product],
    policy: PricingPolicy,
) -> Quote:
    requested_discount = _rate(request.requested_discount, "requested_discount")
    if not request.quantities:
        raise ValueError("quote requires at least one line")
    reasons: list[str] = []
    applied_discount = min(requested_discount, policy.max_discount)
    if requested_discount > policy.max_discount:
        reasons.append("discount_above_policy")
    lines: list[QuoteLine] = []
    subtotal = Decimal("0")
    discount_multiplier = Decimal("1") - Decimal(str(applied_discount))
    for sku, quantity in sorted(request.quantities.items()):
        if sku not in products:
            raise ValueError(f"unknown sku: {sku}")
        if quantity <= 0:
            raise ValueError("quote quantities must be positive")
        product = products[sku]
        if quantity > product.available_units:
            reasons.append(f"insufficient_inventory:{sku}")
        unit_price = (product.list_price * discount_multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if unit_price <= 0:
            raise ValueError("discounted unit price must be positive")
        extended = unit_price * quantity
        margin = float((unit_price - product.unit_cost) / unit_price)
        if margin < policy.min_gross_margin:
            reasons.append(f"margin_below_floor:{sku}")
        lines.append(QuoteLine(sku, quantity, unit_price, extended, margin))
        subtotal += product.list_price * quantity
    total = sum((line.extended_price for line in lines), Decimal("0"))
    if total >= policy.material_quote_value:
        reasons.append("material_quote_value")
    return Quote(
        request.quote_id,
        tuple(lines),
        subtotal.quantize(Decimal("0.01")),
        requested_discount,
        applied_discount,
        total.quantize(Decimal("0.01")),
        bool(reasons),
        tuple(sorted(set(reasons))),
    )


@dataclass(frozen=True)
class VisibilityObservation:
    prompt_id: str
    engine: str
    brand_mentioned: bool
    brand_cited: bool
    competitor_mentions: int = 0
    sentiment: float = 0.0


def geo_visibility(observations: Iterable[VisibilityObservation]) -> Mapping[str, float]:
    items = list(observations)
    if any(item.competitor_mentions < 0 or not -1 <= item.sentiment <= 1 for item in items):
        raise ValueError("invalid visibility observation")
    count = len(items)
    mentions = sum(item.brand_mentioned for item in items)
    citations = sum(item.brand_cited for item in items)
    total_entities = mentions + sum(item.competitor_mentions for item in items)
    return {
        "observations": float(count),
        "mention_rate": mentions / count if count else 0.0,
        "citation_rate": citations / count if count else 0.0,
        "share_of_voice": mentions / total_entities if total_entities else 0.0,
        "average_sentiment": sum(item.sentiment for item in items) / count if count else 0.0,
    }


@dataclass(frozen=True)
class BrandPolicy:
    required_phrases: tuple[str, ...] = ()
    forbidden_phrases: tuple[str, ...] = ()
    maximum_characters: int | None = None


def check_brand(text: str, policy: BrandPolicy) -> tuple[str, ...]:
    lowered = text.lower()
    violations = [
        f"missing_required:{phrase}"
        for phrase in policy.required_phrases
        if phrase.lower() not in lowered
    ]
    violations.extend(
        f"forbidden_phrase:{phrase}"
        for phrase in policy.forbidden_phrases
        if phrase.lower() in lowered
    )
    if policy.maximum_characters is not None:
        if policy.maximum_characters < 0:
            raise ValueError("maximum_characters must be nonnegative")
        if len(text) > policy.maximum_characters:
            violations.append("maximum_characters_exceeded")
    return tuple(violations)
