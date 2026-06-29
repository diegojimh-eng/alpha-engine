"""
app/routers/valuation_router.py
=================================
FastAPI router handling the valuation form page and calculation endpoint.

GET  /valuation   → renders the input form HTML page
POST /calculate   → accepts JSON body, runs DCF, returns JSON result
"""

from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
import os

from app.models.valuation_models import ValuationRequest, ValuationResponse
from app.adapters.dcf_adapter import run_valuation

router = APIRouter()

# Templates directory is resolved relative to this file's location
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)


@router.get("/valuation", response_class=HTMLResponse)
async def valuation_form(request: Request):
    """Render the DCF input form."""
    return templates.TemplateResponse(
        "valuation_form.html",
        {"request": request},
    )


@router.post("/calculate", response_model=ValuationResponse)
async def calculate(request: Request, body: ValuationRequest):
    """
    Run the DCF valuation engine and return structured results.

    The adapter layer maps the validated Pydantic body to engine inputs,
    calls calculate_dcf(), and maps the result back to a JSON response.
    """
    try:
        result = run_valuation(body)
        return result
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Valuation engine error: {str(e)}")
