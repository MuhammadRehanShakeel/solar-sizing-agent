"""
admin_routes.py - The installer's side (staff login needed).

  GET /admin/stats              numbers for the dashboard
  GET /admin/leads              customers who asked for a call-back (filter by status)
  PUT /admin/leads/{id}         change status (new -> contacted -> site_visit -> won / lost) and notes
  GET /admin/surveys            site-survey bookings (filter by status)
  PUT /admin/surveys/{id}       confirm / done / cancel + notes
  GET /admin/chats              recent chats (also the ones without a lead)
  GET /admin/chats/{session}    one full conversation + its latest quote
  GET /admin/prices             the price list
  PUT /admin/prices             (admin) change prices - every new quote uses them at once
  GET /admin/audit              (admin) who did what
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from app import config
from app.core.auth import ADMIN, STAFF
from app.core.security import client_ip
from app.database import execute_query
from app.schemas import LeadUpdate, PriceUpdate, SurveyUpdate
from app.services import store
from app.services.audit import audit
from app.services.prices import DEFAULT_PRICES, price_rows

router = APIRouter(prefix="/admin", tags=["Installer admin"])
PRICE_LIMITS = (0, 10_000_000)


@router.get("/stats")
def stats(days: int = 30, current_user: dict = Depends(STAFF)):
    days = max(1, min(days, 365))
    period = "created_at >= DATEADD(day, -?, SYSDATETIME())"
    chats = execute_query(f"SELECT COUNT(*) AS n FROM ChatSessions WHERE {period} AND turns > 0", (days,),
                          fetch_one=True)["n"]
    quotes = execute_query(f"SELECT COUNT(*) AS n, AVG(CAST(recommended_kw AS FLOAT)) AS avg_kw, "
                           f"SUM(CAST(recommended_cost AS BIGINT)) AS value FROM Quotes WHERE {period}", (days,),
                           fetch_one=True)
    by_option = execute_query(f"SELECT recommended AS name, COUNT(*) AS n FROM Quotes WHERE {period} "
                              "GROUP BY recommended", (days,), fetch_all=True) or []
    by_city = execute_query(f"SELECT TOP 8 city AS name, COUNT(*) AS n FROM Quotes WHERE {period} "
                            "GROUP BY city ORDER BY COUNT(*) DESC", (days,), fetch_all=True) or []
    leads = execute_query(f"SELECT status AS name, COUNT(*) AS n FROM Leads WHERE {period} GROUP BY status", (days,),
                          fetch_all=True) or []
    by_day = execute_query(f"SELECT CONVERT(date, created_at) AS day, COUNT(*) AS n FROM Quotes WHERE {period} "
                           "GROUP BY CONVERT(date, created_at) ORDER BY day", (days,), fetch_all=True) or []
    models = execute_query(f"SELECT ISNULL(model, 'none') AS name, COUNT(*) AS n FROM ChatMessages WHERE {period} "
                           "AND role = 'assistant' GROUP BY model", (days,), fetch_all=True) or []
    surveys = execute_query(f"SELECT COUNT(*) AS n FROM SurveyBookings WHERE {period}", (days,),
                            fetch_one=True)["n"]
    total_leads = sum(r["n"] for r in leads)
    won = sum(r["n"] for r in leads if r["name"] == "won")
    return {"chats": chats, "quotes": quotes["n"], "average_kw": round(quotes["avg_kw"] or 0, 1),
            "quoted_value": quotes["value"] or 0, "leads": total_leads, "won": won, "surveys": surveys,
            "chat_to_lead_percent": round(100 * total_leads / chats) if chats else 0,
            "by_option": by_option, "by_city": by_city, "leads_by_status": leads,
            "by_day": [{"day": str(r["day"]), "n": r["n"]} for r in by_day], "models": models}


@router.get("/leads")
def leads(status: str = None, current_user: dict = Depends(STAFF)):
    where, params = "", ()
    if status in ("new", "contacted", "site_visit", "won", "lost"):
        where, params = "WHERE l.status = ?", (status,)
    return execute_query(
        "SELECT l.lead_id, l.session_id, l.customer_name, l.phone, l.city, l.preferred_option, l.status, l.notes, "
        "l.created_at, l.updated_at, q.public_token, q.recommended_kw, q.recommended_cost, q.average_units, "
        f"u.full_name AS updated_by_name FROM Leads l LEFT JOIN Quotes q ON l.quote_id = q.quote_id "
        f"LEFT JOIN Users u ON l.updated_by = u.user_id {where} ORDER BY l.lead_id DESC", params, fetch_all=True) or []


@router.put("/leads/{lead_id}")
def update_lead(lead_id: int, body: LeadUpdate, request: Request, current_user: dict = Depends(STAFF)):
    lead = execute_query("SELECT lead_id, status FROM Leads WHERE lead_id = ?", (lead_id,), fetch_one=True)
    if not lead:
        raise HTTPException(404, "Lead not found.")
    execute_query("UPDATE Leads SET status = ISNULL(?, status), notes = ISNULL(?, notes), updated_by = ?, "
                  "updated_at = SYSDATETIME() WHERE lead_id = ?",
                  (body.status, body.notes, current_user["user_id"], lead_id), commit=True)
    audit(current_user["user_id"], "lead_updated", str(lead_id),
          f"{lead['status']} -> {body.status}" if body.status else "notes", client_ip(request))
    return {"status": "success"}


@router.get("/surveys")
def surveys(status: str = None, current_user: dict = Depends(STAFF)):
    where, params = "", ()
    if status in ("requested", "confirmed", "done", "cancelled"):
        where, params = "WHERE b.status = ?", (status,)
    rows = execute_query(
        "SELECT b.booking_id, b.session_id, b.customer_name, b.phone, b.area, b.preferred_date, b.time_slot, "
        "b.status, b.notes, b.created_at, q.public_token, q.recommended, q.recommended_kw, q.recommended_cost "
        f"FROM SurveyBookings b LEFT JOIN Quotes q ON b.quote_id = q.quote_id {where} "
        "ORDER BY CASE b.status WHEN 'requested' THEN 0 WHEN 'confirmed' THEN 1 ELSE 2 END, b.preferred_date",
        params, fetch_all=True) or []
    for r in rows:
        r["preferred_date"] = str(r["preferred_date"])
    return rows


@router.put("/surveys/{booking_id}")
def update_survey(booking_id: int, body: SurveyUpdate, request: Request, current_user: dict = Depends(STAFF)):
    row = execute_query("SELECT booking_id, status FROM SurveyBookings WHERE booking_id = ?", (booking_id,),
                        fetch_one=True)
    if not row:
        raise HTTPException(404, "Booking not found.")
    execute_query("UPDATE SurveyBookings SET status = ISNULL(?, status), notes = ISNULL(?, notes), updated_by = ?, "
                  "updated_at = SYSDATETIME() WHERE booking_id = ?",
                  (body.status, body.notes, current_user["user_id"], booking_id), commit=True)
    audit(current_user["user_id"], "survey_updated", str(booking_id),
          f"{row['status']} -> {body.status}" if body.status else "notes", client_ip(request))
    return {"status": "success"}


@router.get("/chats")
def chats(current_user: dict = Depends(STAFF)):
    return execute_query(
        "SELECT TOP 100 s.session_id, s.turns, s.created_at, s.last_active, s.channel, q.recommended, q.recommended_kw, "
        "q.city, l.customer_name, l.status AS lead_status FROM ChatSessions s "
        "LEFT JOIN Quotes q ON q.quote_id = s.latest_quote_id LEFT JOIN Leads l ON l.session_id = s.session_id "
        "WHERE s.turns > 0 ORDER BY s.last_active DESC", fetch_all=True) or []


@router.get("/chats/{session_id}")
def chat_detail(session_id: str, current_user: dict = Depends(STAFF)):
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Chat not found.")
    quote = store.get_quote(quote_id=session["latest_quote_id"]) if session["latest_quote_id"] else None
    return {"messages": store.history(session_id), "quote": quote,
            "quote_url": f"{config.PUBLIC_BASE_URL}/quote/{quote['public_token']}" if quote else None}


@router.get("/prices")
def prices(current_user: dict = Depends(STAFF)):
    return price_rows()


@router.put("/prices")
def update_prices(body: PriceUpdate, request: Request, current_user: dict = Depends(ADMIN)):
    changed = []
    for key, value in body.prices.items():
        if key not in DEFAULT_PRICES:
            raise HTTPException(400, f"Unknown price: {key}")
        if not PRICE_LIMITS[0] < value <= PRICE_LIMITS[1] and not (key == "margin_percent" and value == 0):
            raise HTTPException(400, f"Price for '{DEFAULT_PRICES[key][0]}' is not valid.")
        if key == "margin_percent" and value > 60:
            raise HTTPException(400, "Margin above 60 % is not allowed.")
        execute_query("UPDATE Prices SET value = ?, updated_by = ?, updated_at = SYSDATETIME() WHERE price_key = ? "
                      "IF @@ROWCOUNT = 0 INSERT INTO Prices (price_key, value, updated_by) VALUES (?, ?, ?)",
                      (value, current_user["user_id"], key, key, value, current_user["user_id"]), commit=True)
        changed.append(f"{key}={value:g}")
    audit(current_user["user_id"], "prices_changed", None, ", ".join(changed), client_ip(request))
    return price_rows()


@router.get("/audit")
def audit_log(current_user: dict = Depends(ADMIN)):
    return execute_query("SELECT TOP 200 a.audit_id, a.action, a.target, a.details, a.ip_address, a.created_at, "
                         "u.full_name FROM AuditLog a LEFT JOIN Users u ON a.user_id = u.user_id "
                         "ORDER BY a.audit_id DESC", fetch_all=True) or []
