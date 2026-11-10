"""
planner_routes.py - Free tools on the public website (no login, no AI needed).

  GET  /cities            cities for the drop-down (with GPS points for the sunlight data)
  GET  /sunlight          sunlight for a city or a location (NASA POWER), for the "how much sun" chart
  GET  /appliances        appliance list for the backup planner
  POST /backup-plan       ticked appliances + hours -> battery and inverter size, backup hours
  POST /surveys           book a free site survey
"""
from fastapi import APIRouter, HTTPException, Request

from app.core.security import enforce_rate_limit
from app.schemas import BackupPlanIn, SurveyIn
from app.services import appliances, booking, store, sunlight
from app.services.prices import get_prices

router = APIRouter(tags=["Free tools"])


@router.get("/cities")
def cities():
    return [{"key": k, "name": k.title(), "lat": lat, "lon": lon} for k, (lat, lon, _) in sunlight.CITIES.items()]


@router.get("/sunlight")
def sun(request: Request, city: str = "islamabad", lat: float = None, lon: float = None):
    enforce_rate_limit(request, "sunlight", (30, 60))
    data = sunlight.solar_yield(city, lat, lon)
    return {**data, "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]}


@router.get("/appliances")
def appliance_list():
    return appliances.catalogue()


@router.post("/backup-plan")
def backup_plan(body: BackupPlanIn, request: Request):
    enforce_rate_limit(request, "backup_plan", (60, 60))
    return appliances.plan([a.model_dump() for a in body.appliances], body.hours_needed,
                           get_prices()["battery_pack_kwh"])


@router.post("/surveys", status_code=201)
def book_survey(body: SurveyIn, request: Request):
    enforce_rate_limit(request, "survey", (5, 3600))
    if not body.consent:
        raise HTTPException(400, "Please tick the box so the installer may call you.")
    session_id = body.session_id if body.session_id and store.get_session(body.session_id) else None
    quote = store.get_quote(token=body.quote_token) if body.quote_token else None
    try:
        return booking.book(session_id, quote["quote_id"] if quote else None, name=body.name, phone=body.phone,
                            area=body.area, preferred_date=body.preferred_date, time_slot=body.time_slot)
    except ValueError as e:
        raise HTTPException(400, str(e))
