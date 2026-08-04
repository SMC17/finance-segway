"""Venture-capital liquidation-preference and conversion-election engine.

The engine enumerates every conversion election for a small preferred stack.
For each candidate it pays non-converting preferences in seniority order and
allocates the residual pro rata to common plus converted preferred.  A
candidate is an equilibrium only when no preferred class can improve its own
payout by changing its election while the other elections remain fixed.

Participating preferred is recorded by the public data model but deliberately
rejected here until its residual-sharing and cap terms are modeled explicitly.
Failing closed is safer than silently treating participating preferred as
non-participating preferred.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import isfinite
from typing import Sequence

TOLERANCE = 1e-9


@dataclass(frozen=True)
class PreferredSecurity:
    """Contract terms for one preferred security class."""

    name: str
    shares: float
    invested: float
    seniority: int
    preference_multiple: float = 1.0
    conversion_ratio: float = 1.0
    participating: bool = False
    participation_cap_multiple: float | None = None

    @property
    def preference_claim(self) -> float:
        return self.invested * self.preference_multiple

    @property
    def as_converted_shares(self) -> float:
        return self.shares * self.conversion_ratio


@dataclass(frozen=True)
class PreferredPayout:
    name: str
    election: str
    payout: float
    preference_claim: float
    as_converted_shares: float


@dataclass(frozen=True)
class LiquidationWaterfall:
    exit_proceeds: float
    preferred: tuple[PreferredPayout, ...]
    common_payout: float
    total_distributed: float
    equilibrium_count: int


def _finite_nonnegative(name: str, value: float) -> float:
    result = float(value)
    if not isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and nonnegative")
    return result


def _validate(
    common_shares: float,
    preferred: Sequence[PreferredSecurity],
) -> tuple[float, tuple[PreferredSecurity, ...]]:
    common = _finite_nonnegative("common_shares", common_shares)
    if common <= 0.0:
        raise ValueError("common_shares must be positive")
    ordered = tuple(
        sorted(preferred, key=lambda security: (-security.seniority, security.name))
    )
    if not ordered:
        raise ValueError("at least one preferred security is required")
    names = [security.name for security in ordered]
    ranks = [security.seniority for security in ordered]
    if any(not name.strip() for name in names):
        raise ValueError("preferred security names must be non-empty")
    if len(names) != len(set(names)):
        raise ValueError("preferred security names must be unique")
    if (
        any(
            isinstance(rank, bool) or not isinstance(rank, int) or rank <= 0
            for rank in ranks
        )
        or len(ranks) != len(set(ranks))
    ):
        raise ValueError("preferred seniority ranks must be unique positive integers")
    for security in ordered:
        _finite_nonnegative(f"{security.name}.shares", security.shares)
        _finite_nonnegative(f"{security.name}.invested", security.invested)
        _finite_nonnegative(
            f"{security.name}.preference_multiple", security.preference_multiple
        )
        _finite_nonnegative(
            f"{security.name}.conversion_ratio", security.conversion_ratio
        )
        if security.participating:
            raise NotImplementedError(
                f"{security.name}: participating preferred requires an explicit capped "
                "residual-sharing engine"
            )
        if security.participation_cap_multiple not in (None, 0, 0.0):
            raise ValueError(
                f"{security.name}: a participation cap is invalid for "
                "non-participating preferred"
            )
    return common, ordered


def _candidate_payouts(
    exit_proceeds: float,
    common_shares: float,
    ordered: Sequence[PreferredSecurity],
    converted: Sequence[bool],
) -> tuple[tuple[float, ...], float]:
    remaining = exit_proceeds
    preference_payouts: list[float] = []
    for security, converts in zip(ordered, converted):
        payout = 0.0 if converts else min(remaining, security.preference_claim)
        preference_payouts.append(payout)
        remaining = max(0.0, remaining - payout)

    converted_shares = sum(
        security.as_converted_shares
        for security, converts in zip(ordered, converted)
        if converts
    )
    common_pool_shares = common_shares + converted_shares
    preferred_payouts = tuple(
        remaining * security.as_converted_shares / common_pool_shares
        if converts
        else preference_payout
        for security, converts, preference_payout in zip(
            ordered, converted, preference_payouts
        )
    )
    common_payout = remaining * common_shares / common_pool_shares
    return preferred_payouts, common_payout


def liquidation_waterfall(
    *,
    exit_proceeds: float,
    common_shares: float,
    preferred: Sequence[PreferredSecurity],
) -> LiquidationWaterfall:
    """Return the preference/conversion equilibrium for an exit.

    Ties retain the preference election.  This makes boundary behavior stable
    and deterministic while leaving the economic payout unchanged.
    """

    proceeds = _finite_nonnegative("exit_proceeds", exit_proceeds)
    common, ordered = _validate(common_shares, preferred)
    stable: list[tuple[tuple[bool, ...], tuple[float, ...], float]] = []

    # product() starts with all-False, so the deterministic tie-break retains
    # preference before considering conversion.
    for elections in product((False, True), repeat=len(ordered)):
        payouts, common_payout = _candidate_payouts(
            proceeds, common, ordered, elections
        )
        no_profitable_deviation = True
        for index in range(len(ordered)):
            alternative = list(elections)
            alternative[index] = not alternative[index]
            alternative_payouts, _ = _candidate_payouts(
                proceeds, common, ordered, alternative
            )
            if alternative_payouts[index] > payouts[index] + TOLERANCE:
                no_profitable_deviation = False
                break
        if no_profitable_deviation:
            stable.append((elections, payouts, common_payout))

    if not stable:
        raise RuntimeError("no stable conversion-election state exists")
    elections, payouts, common_payout = stable[0]
    total = sum(payouts) + common_payout
    if abs(total - proceeds) > max(TOLERANCE, proceeds * TOLERANCE):
        raise RuntimeError(
            f"liquidation waterfall does not conserve proceeds: {total} != {proceeds}"
        )
    lines = tuple(
        PreferredPayout(
            name=security.name,
            election="convert" if converts else "preference",
            payout=payout,
            preference_claim=security.preference_claim,
            as_converted_shares=security.as_converted_shares,
        )
        for security, converts, payout in zip(ordered, elections, payouts)
    )
    return LiquidationWaterfall(
        exit_proceeds=proceeds,
        preferred=lines,
        common_payout=common_payout,
        total_distributed=total,
        equilibrium_count=len(stable),
    )
