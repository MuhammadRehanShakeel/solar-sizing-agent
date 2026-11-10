"""
chat_routes.py - Everything the CUSTOMER uses (no login needed).

  POST /chat/start            new chat -> session_id (the browser keeps it)
  POST /chat                  send a message -> the agent's answer (+ a quote if one was made)
  GET  /chat/{session_id}     the chat so far (used when the page is reloaded)
  POST /chat/bill             upload a bill photo -> read by Gemini -> shown to the customer to check
  POST /chat/bill/confirm     the customer confirmed / corrected the numbers -> the agent continues
  POST /chat/location         optional: browser location -> NASA sunlight for that exact place
  POST /chat/voice            short voice recording -> text (Whisper); the page then sends it as a message
  POST /calculate             the quick calculator (no AI at all - works even without API keys)
"""
import json
import logging

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from app import config
from app.agent import llm
from app.agent.graph import run_agent
from app.core.security import enforce_rate_limit
from app.schemas import BillConfirm, CalculatorIn, ChatIn, LocationIn
from app.services import bill_reader, sizing, store, sunlight, voice
from app.services.prices import get_prices

router = APIRouter(tags=["Customer chat"])
log = logging.getLogger("chat")

IMAGE_SIGNATURES = {"image/jpeg": [b"\xff\xd8\xff"], "image/png": [b"\x89PNG"], "image/webp": [b"RIFF"]}


def _session_or_404(session_id):
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(404, "This chat has expired. Please start a new chat.")
    return session


def _quote_out(quote):
    return {"quote_id": quote["quote_id"], "token": quote.get("token") or quote.get("public_token"),
            "url": quote.get("url"), "result": quote["result"]} if quote else None


def _answer(session, text):
    """Shared by /chat and /chat/bill: run the agent once and save both sides of the conversation."""
    if session["turns"] >= config.MAX_TURNS_PER_SESSION:
        raise HTTPException(429, "This chat is very long. Please start a new chat (your quotes are saved).")
    earlier = [m for m in store.history(session["session_id"], config.HISTORY_MESSAGES) if m["role"] != "event"]
    ctx = {"session_id": session["session_id"]}
    lat, lon = store.session_location(session)
    if lat is not None:
        ctx["location"] = (lat, lon)
    if session["latest_quote_id"]:
        old = store.get_quote(quote_id=session["latest_quote_id"])
        if old:
            ctx["quote"] = {"quote_id": old["quote_id"], "token": old["public_token"], "result": old["result"],
                            "url": f"{config.PUBLIC_BASE_URL}/quote/{old['public_token']}"}
    previous_quote = ctx.get("quote", {}).get("quote_id")
    bill = json.loads(session["bill_data"]) if session["bill_data"] else None

    store.add_message(session["session_id"], "user", text)
    try:
        out = run_agent(ctx, earlier, text, bill, export_rate=get_prices()["export_rate"])
    except HTTPException:
        raise
    except Exception:
        log.exception("Agent failed")
        raise HTTPException(502, "The AI assistant is busy right now. Please try again in a minute, "
                                 "or use the quick calculator.")
    store.add_message(session["session_id"], "assistant", out["reply"], out["model"], out["tools_used"])
    new_quote = ctx.get("quote") if ctx.get("quote", {}).get("quote_id") != previous_quote else None
    return {"reply": out["reply"], "quote": _quote_out(new_quote), "lead_saved": bool(ctx.get("lead")),
            "booking": ctx.get("booking"),
            "tools_used": out["tools_used"], "model": out["model"]}


def _features():
    """What works right now (the page hides buttons for missing keys)."""
    return {"ai_ready": bool(llm.available_models()), "bill_reading": bool(config.GEMINI_API_KEY),
            "voice": bool(config.GROQ_API_KEY), "installer": config.INSTALLER_NAME}


@router.post("/chat/start")
def start(request: Request):
    enforce_rate_limit(request, "chat_start", (10, 60))
    return {"session_id": store.create_session(), **_features()}


@router.post("/chat")
def chat(body: ChatIn, request: Request):
    enforce_rate_limit(request, "chat", config.RATE_LIMIT_CHAT)
    session = _session_or_404(body.session_id)
    return _answer(session, body.message.strip())


@router.get("/chat/{session_id}")
def chat_history(session_id: str):
    session = _session_or_404(session_id)
    quote = store.get_quote(quote_id=session["latest_quote_id"]) if session["latest_quote_id"] else None
    if quote:
        quote["token"] = quote["public_token"]
        quote["url"] = f"{config.PUBLIC_BASE_URL}/quote/{quote['public_token']}"
    return {"session_id": session_id, **_features(),
            "messages": [{"role": m["role"], "content": m["content"], "created_at": m["created_at"]}
                         for m in store.history(session_id)],
            "quote": _quote_out(quote), "bill": json.loads(session["bill_data"]) if session["bill_data"] else None}


@router.post("/chat/bill")
async def upload_bill(request: Request, session_id: str = Form(...), file: UploadFile = File(...)):
    enforce_rate_limit(request, "bill", config.RATE_LIMIT_BILL)
    session = _session_or_404(session_id)
    data = await file.read(config.MAX_BILL_MB * 1024 * 1024 + 1)
    if len(data) > config.MAX_BILL_MB * 1024 * 1024:
        raise HTTPException(413, f"Photo is too big (max {config.MAX_BILL_MB} MB).")
    mime = (file.content_type or "").lower()
    if mime not in config.BILL_TYPES or not any(data.startswith(s) for s in IMAGE_SIGNATURES[mime]):
        raise HTTPException(415, "Please upload a JPG, PNG or WEBP photo of the bill.")
    bill = bill_reader.read_bill(data, mime)                     # the photo is NOT saved anywhere
    bill["confirmed"] = False
    store.save_bill_data(session_id, bill)
    return {"bill": bill}                                        # the page shows it to be checked first


@router.post("/chat/bill/confirm")
def confirm_bill(body: BillConfirm, request: Request):
    """The customer checked (and maybe corrected) what was read from the bill. Then the agent continues."""
    enforce_rate_limit(request, "chat", config.RATE_LIMIT_CHAT)
    session = _session_or_404(body.session_id)
    bill = json.loads(session["bill_data"]) if session["bill_data"] else {}
    units = [u for u in body.monthly_units if u > 0][-12:]
    bill.update({"monthly_units": units, "average_units": round(sum(units) / len(units)), "confirmed": True,
                 "corrected_by_customer": units != bill.get("monthly_units")})
    if body.sanctioned_load_kw:
        bill["sanctioned_load_kw"] = body.sanctioned_load_kw
    store.save_bill_data(body.session_id, bill)
    session["bill_data"] = json.dumps(bill)
    text = (f"[Bill confirmed] {bill.get('disco') or 'Bill'}: {len(units)} months, average "
            f"{bill['average_units']} units/month"
            + (f", sanctioned load {bill['sanctioned_load_kw']:g} kW" if bill.get("sanctioned_load_kw") else "")
            + (". I corrected some numbers." if bill["corrected_by_customer"] else "."))
    return {"bill": bill, **_answer(session, text)}


@router.post("/chat/location")
def share_location(body: LocationIn, request: Request):
    """Optional 'use my location' button: exact NASA sunlight instead of a city average."""
    enforce_rate_limit(request, "location", (10, 60))
    _session_or_404(body.session_id)
    lat, lon, place = sunlight.location_for(None, body.lat, body.lon)
    if lat is None or place != "your location":
        raise HTTPException(400, "This location is outside Pakistan, so the city average is used.")
    store.save_location(body.session_id, lat, lon)
    solar = sunlight.solar_yield(None, lat, lon)
    return {"saved": True, "yearly_kwh_per_kw": solar["yearly_kwh_per_kw"], "source": solar["source"]}


@router.post("/chat/voice")
async def voice_message(request: Request, audio: UploadFile = File(...), language: str = Form("")):
    enforce_rate_limit(request, "voice", config.RATE_LIMIT_VOICE)
    data = await audio.read(config.MAX_AUDIO_MB * 1024 * 1024 + 1)
    if len(data) > config.MAX_AUDIO_MB * 1024 * 1024:
        raise HTTPException(413, "Recording is too long. Keep it under one minute.")
    if len(data) < 1000:
        raise HTTPException(422, "The recording is empty. Hold the mic button while you speak.")
    return {"text": voice.transcribe(data, audio.content_type, language or None)}


@router.post("/calculate")
def calculate(body: CalculatorIn, request: Request):
    enforce_rate_limit(request, "calculate", (30, 60))
    if body.session_id and not store.get_session(body.session_id):
        body.session_id = None
    try:
        lat = lon = None
        if body.session_id:
            lat, lon = store.session_location(store.get_session(body.session_id))
        if body.lat is not None and body.lon is not None:
            lat, lon = body.lat, body.lon
        result = sizing.calculate_options(
            body.monthly_units, body.city, body.outage_hours, body.backup_load_w, body.roof_area_sqft, body.budget_rs,
            body.sanctioned_load_kw, body.has_grid, prices=get_prices(), outage_days_per_week=body.outage_days_per_week,
            outage_start_hour=body.outage_start_hour, outage_end_hour=body.outage_end_hour,
            grid_choice=body.grid_choice, tier=body.package, lat=lat, lon=lon)
    except ValueError as e:
        raise HTTPException(400, str(e))
    saved = store.save_quote(body.session_id, result)
    return {**saved, "result": result}
