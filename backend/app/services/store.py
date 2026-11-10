"""
store.py - Saves and loads chats, quotes and leads (SQL Server).

Customers never log in. A chat is identified by a random 32-character session_id that only
their browser knows (like a long password), and a quote by its own random public_token.
"""
import json
import secrets

from app import config
from app.database import execute_insert_and_get_id, execute_query


def new_id() -> str:
    return secrets.token_hex(16)                       # 32 characters, impossible to guess


# ---------------------------------------------------------------- chats
def create_session(channel: str = "web") -> str:
    session_id = new_id()
    execute_query("INSERT INTO ChatSessions (session_id, channel) VALUES (?, ?)", (session_id, channel), commit=True)
    return session_id


def get_session(session_id: str):
    if not session_id or len(session_id) != 32 or not session_id.isalnum():
        return None
    return execute_query("SELECT session_id, bill_data, latest_quote_id, turns, location FROM ChatSessions "
                         "WHERE session_id = ?", (session_id,), fetch_one=True)


def save_location(session_id, lat: float, lon: float):
    """Rounded to ~1 km: enough for sunlight data, not enough to find a house."""
    execute_query("UPDATE ChatSessions SET location = ? WHERE session_id = ?",
                  (f"{lat:.2f},{lon:.2f}", session_id), commit=True)


def session_location(session):
    try:
        lat, lon = (float(x) for x in (session.get("location") or "").split(","))
        return lat, lon
    except ValueError:
        return None, None


def add_message(session_id, role, content, model=None, tools_used=None):
    execute_query("INSERT INTO ChatMessages (session_id, role, content, model, tools_used) VALUES (?, ?, ?, ?, ?)",
                  (session_id, role, content, model, ",".join(tools_used) if tools_used else None), commit=True)
    if role == "user":
        execute_query("UPDATE ChatSessions SET turns = turns + 1, last_active = SYSDATETIME() WHERE session_id = ?",
                      (session_id,), commit=True)


def history(session_id, limit=None):
    """Oldest first. limit = only the newest N messages."""
    rows = execute_query(
        f"SELECT {'TOP (?)' if limit else ''} message_id, role, content, model, tools_used, created_at "
        "FROM ChatMessages WHERE session_id = ? ORDER BY message_id DESC",
        ((limit, session_id) if limit else (session_id,)), fetch_all=True) or []
    return list(reversed(rows))


def save_bill_data(session_id, data: dict):
    execute_query("UPDATE ChatSessions SET bill_data = ? WHERE session_id = ?",
                  (json.dumps(data), session_id), commit=True)


# ---------------------------------------------------------------- quotes
def save_quote(session_id, result: dict) -> dict:
    token = new_id()
    best = result["options"][result["recommended"]]
    quote_id = execute_insert_and_get_id(
        "INSERT INTO Quotes (session_id, public_token, city, average_units, recommended, recommended_kw, "
        "recommended_cost, result_json) OUTPUT INSERTED.quote_id VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (session_id, token, result["inputs"]["city"], result["inputs"]["average_units"], result["recommended"],
         best["system_kw"], best["cost"]["total"], json.dumps(result)))
    if session_id:
        execute_query("UPDATE ChatSessions SET latest_quote_id = ? WHERE session_id = ?", (quote_id, session_id),
                      commit=True)
    return {"quote_id": quote_id, "token": token, "url": f"{config.PUBLIC_BASE_URL}/quote/{token}"}


def get_quote(quote_id=None, token=None):
    if token is not None and (len(token) != 32 or not token.isalnum()):
        return None
    row = execute_query(
        "SELECT q.quote_id, q.session_id, q.public_token, q.result_json, q.created_at, "
        "l.customer_name FROM Quotes q LEFT JOIN Leads l ON l.quote_id = q.quote_id "
        f"WHERE {'q.quote_id' if quote_id else 'q.public_token'} = ?", (quote_id or token,), fetch_one=True)
    if row:
        row["result"] = json.loads(row.pop("result_json"))
    return row


# ---------------------------------------------------------------- leads
def save_lead(session_id, quote_id, name, phone, city, preferred_option) -> int:
    existing = execute_query("SELECT lead_id FROM Leads WHERE session_id = ?", (session_id,), fetch_one=True)
    if existing:
        execute_query("UPDATE Leads SET customer_name = ?, phone = ?, city = ?, preferred_option = ?, quote_id = ?, "
                      "updated_at = SYSDATETIME() WHERE lead_id = ?",
                      (name, phone, city, preferred_option, quote_id, existing["lead_id"]), commit=True)
        return existing["lead_id"]
    return execute_insert_and_get_id(
        "INSERT INTO Leads (session_id, quote_id, customer_name, phone, city, preferred_option) "
        "OUTPUT INSERTED.lead_id VALUES (?, ?, ?, ?, ?, ?)", (session_id, quote_id, name, phone, city, preferred_option))


# ---------------------------------------------------------------- site surveys
def save_booking(session_id, quote_id, name, phone, area, preferred_date, time_slot) -> int:
    return execute_insert_and_get_id(
        "INSERT INTO SurveyBookings (session_id, quote_id, customer_name, phone, area, preferred_date, time_slot) "
        "OUTPUT INSERTED.booking_id VALUES (?, ?, ?, ?, ?, ?, ?)",
        (session_id, quote_id, name, phone, area, preferred_date, time_slot))
