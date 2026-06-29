"""
valuation_engine/dcf_engine.py
================================
Pure DCF valuation engine.

This module contains ALL financial calculations.
Nothing outside this file should change any formula.

Formulas implemented (matching repo design documented in README):

  FCFF = EBIT * (1 - tax_rate) + depreciation - capex - delta_nwc
  WACC = provided directly by user (matches repo approach)
  Terminal Value (Gordon Growth) = FCFF_N * (1 + g) / (WACC - g)
  PV(TV) = TV / (1 + WACC)^N
  Enterprise Value = sum(PV(FCFF_t)) + PV(TV)
  Equity Value = EV - net_debt
  Fair Value / Share = max(Equity Value, 0) / shares_outstanding

Guard rails (from repo README):
  WACC - g >= 0.30% (spread floor to prevent TV explosion)
  g <= 3.5% (capped at long-run nominal GDP)
  WACC floored at 4%, capped at 40%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


# ---------------------------------------------------------------------------
# Input model
# ---------------------------------------------------------------------------

@dataclass
class DCFInputs:
    """
    All inputs required to run one complete DCF valuation.
    Passed directly from the adapter layer — no transformation of values.
    """
    company_name: str
    currency: str

    # Income statement drivers
    revenue: float               # Base-year revenue (absolute, e.g. 1_000_000)
    revenue_growth_rate: float   # Annual revenue growth rate as decimal (e.g. 0.08)
    operating_margin: float      # EBIT / Revenue as decimal (e.g. 0.20)
    tax_rate: float              # Effective tax rate as decimal (e.g. 0.21)

    # Cash flow adjustments (all as % of revenue, decimals)
    capex_pct_revenue: float         # CapEx / Revenue
    depreciation_pct_revenue: float  # D&A / Revenue
    nwc_change_pct_revenue: float    # Change in Net Working Capital / Revenue

    # Discount rate & terminal value
    wacc: float                  # Weighted Average Cost of Capital, decimal
    terminal_growth_rate: float  # Gordon Growth perpetuity rate, decimal

    # Projection horizon
    projection_years: int        # Number of explicit forecast years (typically 5–10)

    # Equity bridge
    shares_outstanding: float    # Diluted shares (absolute units, not millions)
    cash: float                  # Cash and equivalents
    debt: float                  # Total debt (gross)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

@dataclass
class YearProjection:
    """One year of the explicit forecast period."""
    year: int                    # Calendar year label
    revenue: float
    ebit: float
    nopat: float                 # EBIT * (1 - tax_rate)
    depreciation: float
    capex: float
    delta_nwc: float
    fcff: float                  # Free Cash Flow to Firm
    discount_factor: float       # 1 / (1 + WACC)^t
    pv_fcff: float               # Present value of FCFF


@dataclass
class DCFResult:
    """Complete output of one DCF calculation run."""
    # Per-year projection table
    projections: List[YearProjection]

    # Terminal value components
    terminal_fcff: float         # FCFF in final explicit year
    terminal_value: float        # Gordon Growth terminal value (undiscounted)
    pv_terminal_value: float     # PV of terminal value
    terminal_value_pct_ev: float # TV as % of Enterprise Value

    # Valuation summary
    sum_pv_fcff: float           # Sum of discounted FCFFs
    enterprise_value: float
    net_debt: float              # debt - cash
    equity_value: float
    fair_value_per_share: float

    # Inputs echo (for display)
    inputs: DCFInputs

    # Warnings surfaced during calculation
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core calculation function — THE SOURCE OF TRUTH
# ---------------------------------------------------------------------------

def calculate_dcf(inputs: DCFInputs) -> DCFResult:
    """
    Run a complete DCF valuation from the provided inputs.

    This function is the single point where all financial formulas execute.
    The adapter layer calls this function; it never modifies the logic here.

    Returns a DCFResult with all intermediate and final values.
    """
    warnings: list[str] = []

    # ── Guard rails ─────────────────────────────────────────────────────────
    wacc = max(0.04, min(0.40, inputs.wacc))
    if wacc != inputs.wacc:
        warnings.append(
            f"WACC clamped from {inputs.wacc:.2%} to {wacc:.2%} "
            f"(allowed range: 4%–40%)"
        )

    g = inputs.terminal_growth_rate
    if g > 0.035:
        warnings.append(
            f"Terminal growth rate {g:.2%} exceeds long-run nominal GDP cap of 3.5%. "
            f"Consider using a lower rate."
        )

    spread = wacc - g
    if spread < 0.003:
        # Enforce minimum 30 bps spread to prevent terminal value explosion
        g = wacc - 0.003
        warnings.append(
            f"Terminal growth rate adjusted to {g:.2%} to maintain "
            f"minimum 30 bps WACC–g spread."
        )

    # ── Explicit forecast period ─────────────────────────────────────────────
    import datetime
    base_year = datetime.date.today().year
    projections: list[YearProjection] = []
    current_revenue = inputs.revenue

    for t in range(1, inputs.projection_years + 1):
        # Revenue grows at constant rate each year
        current_revenue = current_revenue * (1 + inputs.revenue_growth_rate)

        # EBIT = Revenue * operating_margin
        ebit = current_revenue * inputs.operating_margin

        # NOPAT = EBIT * (1 - tax_rate)   [Net Operating Profit After Tax]
        nopat = ebit * (1 - inputs.tax_rate)

        # Capex, Depreciation, ΔNWC — all as % of current year revenue
        capex = current_revenue * inputs.capex_pct_revenue
        depreciation = current_revenue * inputs.depreciation_pct_revenue
        delta_nwc = current_revenue * inputs.nwc_change_pct_revenue

        # FCFF = NOPAT + D&A - CapEx - ΔNWC
        fcff = nopat + depreciation - capex - delta_nwc

        # Discount factor = 1 / (1 + WACC)^t
        discount_factor = 1.0 / (1 + wacc) ** t

        # PV of FCFF
        pv_fcff = fcff * discount_factor

        projections.append(YearProjection(
            year=base_year + t,
            revenue=current_revenue,
            ebit=ebit,
            nopat=nopat,
            depreciation=depreciation,
            capex=capex,
            delta_nwc=delta_nwc,
            fcff=fcff,
            discount_factor=discount_factor,
            pv_fcff=pv_fcff,
        ))

    # ── Terminal Value — Gordon Growth Model ─────────────────────────────────
    # TV = FCFF_N * (1 + g) / (WACC - g)
    terminal_fcff = projections[-1].fcff
    terminal_value = terminal_fcff * (1 + g) / (wacc - g)

    # PV(TV) = TV / (1 + WACC)^N
    pv_terminal_value = terminal_value / (1 + wacc) ** inputs.projection_years

    # Warn if TV dominates (>80%)
    sum_pv_fcff = sum(p.pv_fcff for p in projections)
    rough_ev = sum_pv_fcff + pv_terminal_value
    if rough_ev > 0:
        tv_pct = pv_terminal_value / rough_ev
        if tv_pct > 0.80:
            warnings.append(
                f"Terminal value represents {tv_pct:.0%} of Enterprise Value. "
                f"Results are highly sensitive to the terminal growth rate assumption."
            )
    else:
        tv_pct = 0.0

    # ── Enterprise Value ─────────────────────────────────────────────────────
    enterprise_value = sum_pv_fcff + pv_terminal_value

    # ── Equity Bridge ────────────────────────────────────────────────────────
    # net_debt = debt - cash
    net_debt = inputs.debt - inputs.cash
    equity_value = enterprise_value - net_debt

    # Fair Value per Share = max(Equity Value, 0) / shares_outstanding
    if inputs.shares_outstanding > 0:
        fair_value_per_share = max(equity_value, 0.0) / inputs.shares_outstanding
    else:
        fair_value_per_share = 0.0
        warnings.append("Shares outstanding is zero — cannot compute per-share value.")

    if equity_value < 0:
        warnings.append(
            f"Equity value is negative ({equity_value:,.0f} {inputs.currency}). "
            f"Net debt exceeds Enterprise Value."
        )

    return DCFResult(
        projections=projections,
        terminal_fcff=terminal_fcff,
        terminal_value=terminal_value,
        pv_terminal_value=pv_terminal_value,
        terminal_value_pct_ev=tv_pct,
        sum_pv_fcff=sum_pv_fcff,
        enterprise_value=enterprise_value,
        net_debt=net_debt,
        equity_value=equity_value,
        fair_value_per_share=fair_value_per_share,
        inputs=inputs,
        warnings=warnings,
    )
