"""Corporate operating-model reference engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .common import clamp, require_finite, require_nonnegative


@dataclass(frozen=True)
class OperatingAssumptions:
    revenue_growth: Sequence[float]
    ebitda_margin: Sequence[float]
    capex_pct_revenue: Sequence[float]
    nwc_pct_revenue: Sequence[float]
    tax_rate: Sequence[float]
    depreciation_pct_opening_ppe: Sequence[float] | None = None

    def periods(self) -> int:
        lengths = {
            len(self.revenue_growth),
            len(self.ebitda_margin),
            len(self.capex_pct_revenue),
            len(self.nwc_pct_revenue),
            len(self.tax_rate),
        }
        if self.depreciation_pct_opening_ppe is not None:
            lengths.add(len(self.depreciation_pct_opening_ppe))
        if len(lengths) != 1:
            raise ValueError("all operating-assumption vectors must have equal length")
        count = lengths.pop()
        if count <= 0:
            raise ValueError("at least one forecast period is required")
        return count


@dataclass(frozen=True)
class OperatingPeriod:
    period: int
    revenue: float
    ebitda: float
    depreciation: float
    ebit: float
    taxes: float
    capex: float
    nwc: float
    change_nwc: float
    unlevered_fcf: float
    ending_ppe: float


def forecast_operating(
    *, opening_revenue: float, opening_ppe: float, opening_nwc: float,
    assumptions: OperatingAssumptions,
) -> list[OperatingPeriod]:
    """Build a deterministic operating forecast with explicit FCF identities."""
    revenue = require_nonnegative("opening_revenue", opening_revenue)
    ppe = require_nonnegative("opening_ppe", opening_ppe)
    nwc = require_finite("opening_nwc", opening_nwc)
    periods = assumptions.periods()
    depreciation_rates = assumptions.depreciation_pct_opening_ppe or [0.0] * periods
    output: list[OperatingPeriod] = []
    for i in range(periods):
        growth = require_finite("revenue_growth", assumptions.revenue_growth[i])
        margin = require_finite("ebitda_margin", assumptions.ebitda_margin[i])
        capex_pct = require_nonnegative("capex_pct_revenue", assumptions.capex_pct_revenue[i])
        nwc_pct = require_finite("nwc_pct_revenue", assumptions.nwc_pct_revenue[i])
        tax_rate = clamp(require_finite("tax_rate", assumptions.tax_rate[i]), 0.0, 1.0)
        depreciation_rate = require_nonnegative("depreciation_pct_opening_ppe", depreciation_rates[i])
        revenue = max(0.0, revenue * (1.0 + growth))
        ebitda = revenue * margin
        depreciation = min(ppe, ppe * depreciation_rate)
        ebit = ebitda - depreciation
        taxes = max(0.0, ebit * tax_rate)
        capex = revenue * capex_pct
        next_nwc = revenue * nwc_pct
        change_nwc = next_nwc - nwc
        unlevered_fcf = ebitda - taxes - capex - change_nwc
        ending_ppe = max(0.0, ppe + capex - depreciation)
        output.append(OperatingPeriod(
            i + 1, revenue, ebitda, depreciation, ebit, taxes, capex,
            next_nwc, change_nwc, unlevered_fcf, ending_ppe,
        ))
        ppe, nwc = ending_ppe, next_nwc
    return output
