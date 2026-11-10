"""
bill_reader.py - Reads a photo of an electricity bill (IESCO, LESCO, MEPCO, ...) with Gemini.

Gemini can "see" images. We ask it to fill a fixed JSON form (response_schema), so the answer
is always the same shape. Then Python checks every number before we trust it.

Privacy: we ask ONLY for numbers (units, load, tariff). The name, address and reference
number on the bill are not requested, and the photo itself is never saved.
"""
import json
import logging

from fastapi import HTTPException
from pydantic import BaseModel, Field

from app import config

log = logging.getLogger("bill_reader")


class MonthUnits(BaseModel):
    month: str = Field(description="Month as printed, e.g. 'Sep 25' or 'SEP-25'")
    units: int = Field(description="Units (kWh) used in that month")


class BillData(BaseModel):
    is_electricity_bill: bool = Field(description="False if the photo is not a Pakistani electricity bill")
    disco: str | None = Field(None, description="Company short name, e.g. IESCO, LESCO, MEPCO, K-Electric")
    tariff: str | None = Field(None, description="Tariff code, e.g. A-1a(01)")
    sanctioned_load_kw: float | None = Field(None, description="Sanctioned / connected load in kW")
    current_units: int | None = Field(None, description="Units consumed in the bill month")
    amount_payable: int | None = Field(None, description="Amount payable within due date, Rs")
    history: list[MonthUnits] = Field(default_factory=list,
                                      description="The bill history table: up to 12 previous months with units")
    has_solar_net_metering: bool | None = Field(None, description="True if export / net-metering units are shown")


PROMPT = """You are reading a photo of a Pakistani electricity bill.
Fill in the form from what is printed. Copy numbers exactly; do not guess.
If a value is not visible, leave it empty. The 'history' is the table of previous months (MONTH / UNITS / BILL).
Do NOT copy the customer's name, address, CNIC or reference number."""


def check(data: BillData) -> dict:
    """Throw away impossible numbers (a misread digit must not become a 50 kW system)."""
    if not data.is_electricity_bill:
        raise HTTPException(422, "This does not look like an electricity bill. Please upload a clear photo of "
                                 "the full bill, or just type your monthly units.")
    history = [{"month": h.month[:12], "units": h.units} for h in data.history if 0 < h.units <= 20000][:12]
    units = [h["units"] for h in history]
    if data.current_units and 0 < data.current_units <= 20000:
        units.append(data.current_units)
    if not units:
        raise HTTPException(422, "I could not read the units on this bill. Please try a sharper photo, or type "
                                 "your monthly units.")
    load = data.sanctioned_load_kw if data.sanctioned_load_kw and 0 < data.sanctioned_load_kw <= 100 else None
    return {
        "disco": (data.disco or "")[:20] or None, "tariff": (data.tariff or "")[:20] or None,
        "sanctioned_load_kw": load, "current_units": data.current_units,
        "amount_payable": data.amount_payable if data.amount_payable and data.amount_payable < 5_000_000 else None,
        "history": history, "monthly_units": units[-12:],
        "average_units": round(sum(units[-12:]) / len(units[-12:])),
        "has_solar_net_metering": data.has_solar_net_metering,
    }


def read_bill(image: bytes, mime_type: str) -> dict:
    if not config.GEMINI_API_KEY:
        raise HTTPException(503, "Bill reading needs a GEMINI_API_KEY in backend/.env. You can type your units instead.")
    from google import genai
    from google.genai import types
    from app.services import gemini
    client = gemini.make_client()
    try:
        response = gemini.generate_with_backups(
            client,
            contents=[types.Part.from_bytes(data=image, mime_type=mime_type), PROMPT],
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=BillData,
                                               temperature=0),
        )
        data = response.parsed if isinstance(response.parsed, BillData) else BillData(**json.loads(response.text))
    except HTTPException:
        raise
    except Exception as e:
        log.exception("Gemini could not read the bill")
        raise HTTPException(502, "The bill reader is busy right now. Please try again in a minute or type your units.")
    return check(data)
