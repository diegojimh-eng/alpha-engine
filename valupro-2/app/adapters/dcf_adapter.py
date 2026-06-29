"""
app/adapters/dcf_adapter.py
=============================
Adapter layer — translates Pydantic models ↔ valuation engine dataclasses.
No financial logic lives here. Only data shape conversion.
"""

from __future__ import annotations

from valuation_engine import DCFInputs, DCFResult, calculate_dcf
from app.models.valuation_models import (
    ValuationRequest,
    ValuationResponse,
    ValuationSummary,
    YearProjectionResponse,
)


def request_to_inputs(req: ValuationRequest) -> DCFInputs:
    """
    Map a validated ValuationRequest to DCFInputs.
    The pct_to_decimal validator in ValuationRequest has already converted
    all percent fields to decimals — passed through unchanged.
    """
    return DCFInputs(
        company_name=req.company_name,
        currency=req.currency,
        revenue=req.revenue,
        revenue_growth_rate=req.revenue_growth_rate,
        operating_margin=req.operating_margin,
        tax_rate=req.tax_rate,
        capex_pct_revenue=req.capex_pct_revenue,
        depreciation_pct_revenue=req.depreciation_pct_revenue,
        nwc_change_pct_revenue=req.nwc_change_pct_revenue,
        wacc=req.wacc,
        terminal_growth_rate=req.terminal_growth_rate,
        projection_years=req.projection_years,
        shares_outstanding=req.shares_outstanding,
        cash=req.cash,
        debt=req.debt,
    )


def result_to_response(result: DCFResult) -> ValuationResponse:
    """Map a DCFResult to a ValuationResponse. All values passed through unchanged."""
    summary = ValuationSummary(
        enterprise_value=result.enterprise_value,
        net_debt=result.net_debt,
        equity_value=result.equity_value,
        fair_value_per_share=result.fair_value_per_share,
        terminal_value=result.terminal_value,
        pv_terminal_value=result.pv_terminal_value,
        terminal_value_pct_ev=result.terminal_value_pct_ev,
        sum_pv_fcff=result.sum_pv_fcff,
    )

    projections = [
        YearProjectionResponse(
            year=p.year,
            revenue=p.revenue,
            ebit=p.ebit,
            nopat=p.nopat,
            depreciation=p.depreciation,
            capex=p.capex,
            delta_nwc=p.delta_nwc,
            fcff=p.fcff,
            discount_factor=p.discount_factor,
            pv_fcff=p.pv_fcff,
        )
        for p in result.projections
    ]

    return ValuationResponse(
        company_name=result.inputs.company_name,
        currency=result.inputs.currency,
        summary=summary,
        projections=projections,
        warnings=result.warnings,
        chart_years=[p.year for p in result.projections],
        chart_revenue=[p.revenue for p in result.projections],
        chart_fcff=[p.fcff for p in result.projections],
        chart_pv_fcff=[p.pv_fcff for p in result.projections],
    )


def run_valuation(req: ValuationRequest) -> ValuationResponse:
    """Single entry point called by the router."""
    inputs = request_to_inputs(req)
    result = calculate_dcf(inputs)
    return result_to_response(result)
