"""
app/models/valuation_models.py
================================
Pydantic models that validate the HTML form POST body
and structure the API response.

These models are ONLY for data validation and serialisation.
No financial logic lives here.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Request model — maps 1-to-1 with the HTML form fields
# ---------------------------------------------------------------------------

class ValuationRequest(BaseModel):
    """Validated inputs from the web form POST /calculate."""

    company_name: str = Field(..., min_length=1, max_length=200, examples=["Apple Inc."])
    currency: str = Field(default="USD", max_length=10, examples=["USD"])

    # Revenue drivers
    revenue: float = Field(..., gt=0, description="Base-year revenue in absolute units")
    revenue_growth_rate: float = Field(..., description="Annual growth rate as percent, e.g. 8 means 8%")
    operating_margin: float = Field(..., description="EBIT/Revenue as percent, e.g. 20 means 20%")
    tax_rate: float = Field(..., description="Effective tax rate as percent, e.g. 21 means 21%")

    # Cash flow adjustments — entered as % of revenue
    capex_pct_revenue: float = Field(..., description="CapEx as % of revenue, e.g. 5 means 5%")
    depreciation_pct_revenue: float = Field(..., description="D&A as % of revenue, e.g. 3 means 3%")
    nwc_change_pct_revenue: float = Field(..., description="ΔNWC as % of revenue, e.g. 1 means 1%")

    # Discount rate & terminal value
    wacc: float = Field(..., description="WACC as percent, e.g. 9 means 9%")
    terminal_growth_rate: float = Field(..., description="Terminal growth rate as percent, e.g. 2.5 means 2.5%")

    # Projection horizon
    projection_years: int = Field(default=10, ge=1, le=30)

    # Equity bridge
    shares_outstanding: float = Field(..., gt=0, description="Diluted shares outstanding (absolute, not millions)")
    cash: float = Field(default=0.0, ge=0.0, description="Cash and equivalents")
    debt: float = Field(default=0.0, ge=0.0, description="Total gross debt")

    # --- Validators: convert percent → decimal for the engine ---

    @field_validator("revenue_growth_rate", "operating_margin", "tax_rate",
                     "capex_pct_revenue", "depreciation_pct_revenue",
                     "nwc_change_pct_revenue", "wacc", "terminal_growth_rate",
                     mode="before")
    @classmethod
    def pct_to_decimal(cls, v: float) -> float:
        """User enters percentages (e.g. 8); engine expects decimals (0.08)."""
        return float(v) / 100.0

    @model_validator(mode="after")
    def check_wacc_range(self) -> "ValuationRequest":
        if not (0.04 <= self.wacc <= 0.40):
            # Engine will clamp it, but we warn here at the model level too
            pass  # Let the engine handle clamping + warning
        if self.terminal_growth_rate >= self.wacc:
            raise ValueError(
                f"Terminal growth rate ({self.terminal_growth_rate:.2%}) must be "
                f"less than WACC ({self.wacc:.2%}) for a finite terminal value."
            )
        return self


# ---------------------------------------------------------------------------
# Response models — structure returned to the frontend as JSON
# ---------------------------------------------------------------------------

class YearProjectionResponse(BaseModel):
    year: int
    revenue: float
    ebit: float
    nopat: float
    depreciation: float
    capex: float
    delta_nwc: float
    fcff: float
    discount_factor: float
    pv_fcff: float


class ValuationSummary(BaseModel):
    enterprise_value: float
    net_debt: float
    equity_value: float
    fair_value_per_share: float
    terminal_value: float
    pv_terminal_value: float
    terminal_value_pct_ev: float
    sum_pv_fcff: float


class ValuationResponse(BaseModel):
    company_name: str
    currency: str
    summary: ValuationSummary
    projections: List[YearProjectionResponse]
    warnings: List[str]

    # Chart data arrays (pre-computed for Chart.js — avoids JS math)
    chart_years: List[int]
    chart_revenue: List[float]
    chart_fcff: List[float]
    chart_pv_fcff: List[float]
