"""schemas.py - Shapes of the data the API accepts. FastAPI rejects anything that does not fit."""
from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app import config


class ChatIn(BaseModel):
    session_id: str = Field(min_length=32, max_length=32)
    message: str = Field(min_length=1, max_length=config.MAX_MESSAGE_CHARS)


class BillConfirm(BaseModel):
    session_id: str = Field(min_length=32, max_length=32)
    monthly_units: list[int] = Field(min_length=1, max_length=13)
    sanctioned_load_kw: float | None = Field(None, gt=0, le=100)

    @field_validator("monthly_units")
    @classmethod
    def units_in_range(cls, units):
        if not all(0 <= u <= 50_000 for u in units) or not any(units):
            raise ValueError("Units must be between 0 and 50,000, and at least one month above 0.")
        return units


class LocationIn(BaseModel):
    session_id: str = Field(min_length=32, max_length=32)
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class SurveyIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=10, max_length=20)
    area: str = Field(min_length=3, max_length=120)
    preferred_date: date
    time_slot: Literal["morning", "afternoon", "evening"]
    consent: bool
    session_id: str | None = Field(None, min_length=32, max_length=32)
    quote_token: str | None = Field(None, min_length=32, max_length=32)
    website: str = Field("", max_length=0)               # honeypot: bots fill every field


class SurveyUpdate(BaseModel):
    status: Literal["requested", "confirmed", "done", "cancelled"] | None = None
    notes: str | None = Field(None, max_length=1000)


class ApplianceIn(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    quantity: int = Field(1, ge=1, le=50)
    watts: int | None = Field(None, ge=1, le=10000)


class BackupPlanIn(BaseModel):
    appliances: list[ApplianceIn] = Field(min_length=1, max_length=30)
    hours_needed: float = Field(4, gt=0, le=24)


class CalculatorIn(BaseModel):
    monthly_units: list[int] = Field(min_length=1, max_length=12)
    city: str = Field("islamabad", max_length=40)
    outage_hours: float = Field(0, ge=0, le=24)
    outage_days_per_week: int | None = Field(None, ge=0, le=7)
    outage_start_hour: float | None = Field(None, ge=0, le=24)
    outage_end_hour: float | None = Field(None, ge=0, le=24)
    grid_choice: Literal["auto", "net_billing", "no_export", "off_grid"] = "auto"
    package: Literal["economy", "standard", "premium"] = "standard"
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    backup_load_w: int = Field(1500, ge=300, le=20000)
    roof_area_sqft: int | None = Field(None, ge=50, le=100000)
    budget_rs: int | None = Field(None, ge=10000, le=100_000_000)
    sanctioned_load_kw: float | None = Field(None, gt=0, le=100)
    has_grid: bool = True
    session_id: str | None = Field(None, min_length=32, max_length=32)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


class UserIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(max_length=128)
    role: Literal["admin", "sales"] = "sales"


class UserUpdate(BaseModel):
    role: Literal["admin", "sales"] | None = None
    is_active: bool | None = None


class LeadUpdate(BaseModel):
    status: Literal["new", "contacted", "site_visit", "won", "lost"] | None = None
    notes: str | None = Field(None, max_length=1000)


class PriceUpdate(BaseModel):
    prices: dict[str, float]
