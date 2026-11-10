"""The web API: customer chat, bill upload, voice, quotes and the staff/admin side (with security checks)."""
import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.core.security import create_token, hash_password, rate_limiter
from tests.conftest import tool_call

SID = "b" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"0" * 2000


@pytest.fixture(autouse=True)
def fresh_limits():
    rate_limiter._hits.clear()


@pytest.fixture
def client(fake_db):
    from main import app
    fake_db.on("FROM ChatSessions WHERE session_id", lambda p: {"session_id": p[0], "bill_data": None,
                                                                 "latest_quote_id": None, "turns": 0}
               if p[0] == SID else None)
    return TestClient(app)


def staff(fake_db, role="sales", user_id=7):
    fake_db.on("FROM Users WHERE user_id", {"user_id": user_id, "full_name": "Test", "email": "t@x.pk", "role": role,
                                             "is_active": 1, "token_version": 0})
    return {"Authorization": "Bearer " + create_token(user_id, "t@x.pk", role)}


# ------------------------------------------------------------------ customer
def test_start_gives_a_random_session(client, fake_db):
    a, b = client.post("/chat/start").json(), client.post("/chat/start").json()
    assert len(a["session_id"]) == 32 and a["session_id"] != b["session_id"]
    assert a["ai_ready"] is False                      # no keys in tests


def test_chat_end_to_end_returns_the_quote(client, fake_db, scripted):
    scripted([tool_call("calculate_solar_options", {"monthly_units": [450], "city": "Rawalpindi",
                                                    "outage_hours_per_day": 3}),
              AIMessage("Hybrid 5.27 kW is best.")])
    r = client.post("/chat", json={"session_id": SID, "message": "450 units, Pindi, 3 ghante load shedding"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["reply"] == "Hybrid 5.27 kW is best."
    assert body["quote"]["result"]["recommended"] == "hybrid" and len(body["quote"]["token"]) == 32
    saved = [c[1] for c in fake_db.ran("INSERT INTO ChatMessages")]
    assert [s[1] for s in saved] == ["user", "assistant"]
    assert saved[1][3] == "scripted-test-model" and saved[1][4] == "calculate_solar_options"


def test_chat_without_any_ai_key_explains_and_points_to_calculator(client):
    r = client.post("/chat", json={"session_id": SID, "message": "hello"})
    assert r.status_code == 503 and "calculator" in r.json()["detail"]


def test_unknown_session_and_bad_input_are_refused(client, scripted):
    scripted([AIMessage("hi")])
    assert client.post("/chat", json={"session_id": "c" * 32, "message": "hi"}).status_code == 404
    assert client.post("/chat", json={"session_id": "x", "message": "hi"}).status_code == 422
    assert client.post("/chat", json={"session_id": SID, "message": "a" * 1001}).status_code == 422
    assert client.get("/chat/'; DROP TABLE Users--").status_code == 404


def test_long_chats_are_stopped(client, fake_db, scripted):
    scripted([AIMessage("hi")])
    fake_db.on("FROM ChatSessions WHERE session_id", {"session_id": SID, "bill_data": None, "latest_quote_id": None,
                                                      "turns": 40})
    assert client.post("/chat", json={"session_id": SID, "message": "hi"}).status_code == 429


def test_chat_is_rate_limited(client, scripted):
    scripted([AIMessage("ok")] * 30)
    codes = [client.post("/chat", json={"session_id": SID, "message": "hi"}).status_code for _ in range(22)]
    assert codes.count(429) >= 1


def test_bill_upload_checks_the_file_before_any_ai(client, monkeypatch):
    called = []
    monkeypatch.setattr("app.services.bill_reader.read_bill", lambda *a: called.append(1))
    fake_png = {"session_id": SID}
    r = client.post("/chat/bill", data=fake_png, files={"file": ("bill.png", b"MZ\x90\x00 not an image", "image/png")})
    assert r.status_code == 415
    r = client.post("/chat/bill", data=fake_png, files={"file": ("bill.pdf", JPEG, "application/pdf")})
    assert r.status_code == 415 and not called


def test_bill_upload_is_checked_by_the_customer_before_the_agent_continues(client, fake_db, scripted, monkeypatch):
    bill = {"disco": "IESCO", "monthly_units": [400, 420, 380], "average_units": 400, "sanctioned_load_kw": 5,
            "history": [], "current_units": 380, "amount_payable": 21000, "tariff": "A-1a", "has_solar_net_metering": None}
    monkeypatch.setattr("app.routes.chat_routes.bill_reader.read_bill", lambda data, mime: dict(bill))
    model = scripted([AIMessage("Got it: about 410 units a month. Which city?")])
    r = client.post("/chat/bill", data={"session_id": SID}, files={"file": ("b.jpg", JPEG, "image/jpeg")})
    assert r.status_code == 200, r.text
    assert r.json()["bill"]["confirmed"] is False and "reply" not in r.json()     # AI waits for the customer
    assert not model.seen
    saved = json.loads(fake_db.ran("UPDATE ChatSessions SET bill_data")[0][1][0])
    assert saved["disco"] == "IESCO"

    # the customer corrects one month and confirms
    fake_db.on("FROM ChatSessions", {"session_id": SID, "bill_data": json.dumps(saved), "latest_quote_id": None,
                                     "turns": 1, "location": None})
    r = client.post("/chat/bill/confirm", json={"session_id": SID, "monthly_units": [400, 450, 380]})
    assert r.status_code == 200, r.text
    assert r.json()["bill"]["confirmed"] is True and r.json()["bill"]["corrected_by_customer"] is True
    assert "Which city" in r.json()["reply"]
    assert "410" in model.seen[0][0].content                     # the agent sees the corrected numbers


def test_bill_confirm_rejects_impossible_units(client, fake_db):
    r = client.post("/chat/bill/confirm", json={"session_id": SID, "monthly_units": [400, 999999]})
    assert r.status_code == 422


def test_bill_reader_throws_away_impossible_numbers():
    from fastapi import HTTPException

    from app.services.bill_reader import BillData, check
    data = check(BillData(is_electricity_bill=True, sanctioned_load_kw=900, current_units=410,
                          history=[{"month": "Sep 25", "units": 390}, {"month": "Aug 25", "units": 99999}]))
    assert data["monthly_units"] == [390, 410] and data["sanctioned_load_kw"] is None
    with pytest.raises(HTTPException):
        check(BillData(is_electricity_bill=False))


def test_voice_needs_a_key_and_a_real_recording(client):
    assert client.post("/chat/voice", files={"audio": ("v.webm", b"x" * 10, "audio/webm")}).status_code == 422
    assert client.post("/chat/voice", files={"audio": ("v.webm", b"x" * 5000, "audio/webm")}).status_code == 503


def test_voice_text_comes_back(client, monkeypatch):
    monkeypatch.setattr("app.routes.chat_routes.voice.transcribe", lambda data, mime, lang: "mera bill 30 hazar hai")
    r = client.post("/chat/voice", files={"audio": ("v.webm", b"x" * 5000, "audio/webm")})
    assert r.json()["text"] == "mera bill 30 hazar hai"


def test_quick_calculator_works_without_ai(client, fake_db):
    r = client.post("/calculate", json={"monthly_units": [350, 400], "city": "lahore", "outage_hours": 0})
    assert r.status_code == 200
    assert r.json()["result"]["recommended"] == "on_grid" and fake_db.ran("INSERT INTO Quotes")
    assert client.post("/calculate", json={"monthly_units": [], "city": "x"}).status_code == 422


# ------------------------------------------------------------------ quotations
def test_quote_link_and_pdf(client, fake_db):
    from app.services.sizing import calculate_options
    result = calculate_options([500], "islamabad", outage_hours=3)
    fake_db.on("FROM Quotes q", lambda p: {"quote_id": 5, "session_id": SID, "public_token": "d" * 32,
                                           "result_json": json.dumps(result), "created_at": datetime(2026, 10, 27),
                                           "customer_name": "Ali"} if p[0] == "d" * 32 else None)
    assert client.get("/quotes/" + "e" * 32).status_code == 404
    assert client.get("/quotes/short").status_code == 404
    assert client.get("/quotes/" + "d" * 32).json()["result"]["recommended"] == "hybrid"
    pdf = client.get("/quotes/" + "d" * 32 + "/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")


# ------------------------------------------------------------------ staff
def test_admin_pages_need_login(client):
    for path in ("/admin/leads", "/admin/stats", "/admin/prices", "/admin/chats", "/users", "/admin/audit"):
        assert client.get(path).status_code == 401
    assert client.get("/admin/leads", headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_sales_can_work_leads_but_not_change_prices(client, fake_db):
    h = staff(fake_db, "sales")
    fake_db.on("FROM Leads WHERE lead_id", {"lead_id": 3, "status": "new"})
    assert client.get("/admin/leads", headers=h).status_code == 200
    assert client.put("/admin/leads/3", json={"status": "contacted"}, headers=h).status_code == 200
    assert client.put("/admin/leads/3", json={"status": "hacked"}, headers=h).status_code == 422
    assert client.put("/admin/prices", json={"prices": {"panel_price_per_watt": 1}}, headers=h).status_code == 403
    assert client.get("/users", headers=h).status_code == 403


def test_admin_changes_prices_with_checks(client, fake_db):
    h = staff(fake_db, "admin")
    assert client.put("/admin/prices", json={"prices": {"panel_price_per_watt": 38}}, headers=h).status_code == 200
    assert fake_db.ran("UPDATE Prices SET value")[0][1][0] == 38
    assert client.put("/admin/prices", json={"prices": {"evil": 1}}, headers=h).status_code == 400
    assert client.put("/admin/prices", json={"prices": {"battery_per_kwh": -5}}, headers=h).status_code == 400
    assert client.put("/admin/prices", json={"prices": {"margin_percent": 90}}, headers=h).status_code == 400
    assert fake_db.ran("INSERT INTO AuditLog")


def test_quote_token_is_not_a_login(client, fake_db):
    import jwt

    from app import config
    token = jwt.encode({"scope": "quote", "user_id": 1}, config.JWT_SECRET, algorithm="HS256")
    staff(fake_db, "admin", 1)
    assert client.get("/admin/leads", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_disabled_or_logged_out_user_is_refused(client, fake_db):
    h = staff(fake_db, "admin")
    fake_db.on("FROM Users WHERE user_id", {"user_id": 7, "full_name": "T", "email": "t@x.pk", "role": "admin",
                                             "is_active": 1, "token_version": 3})
    assert client.get("/admin/leads", headers=h).status_code == 401
    fake_db.on("FROM Users WHERE user_id", {"user_id": 7, "full_name": "T", "email": "t@x.pk", "role": "admin",
                                             "is_active": 0, "token_version": 0})
    assert client.get("/admin/leads", headers=h).status_code == 401


def test_login_locks_after_five_wrong_passwords(client, fake_db):
    user = {"user_id": 1, "full_name": "A", "email": "a@x.pk", "password_hash": hash_password("Right1234"),
            "role": "admin", "is_active": 1, "failed_logins": 4, "locked_until": None, "token_version": 0}
    fake_db.on("FROM Users WHERE email", user)
    r = client.post("/auth/login", json={"email": "a@x.pk", "password": "wrong"})
    assert r.status_code == 401 and r.json()["detail"] == "Wrong email or password."
    assert fake_db.ran("UPDATE Users SET failed_logins")[0][1][1] is not None          # locked_until set
    assert client.post("/auth/login", json={"email": "nobody@x.pk", "password": "x"}).json()["detail"] == \
        "Wrong email or password."
    ok = client.post("/auth/login", json={"email": "a@x.pk", "password": "Right1234"})
    assert ok.status_code == 200 and ok.json()["user"]["role"] == "admin"


def test_admin_cannot_lock_themselves_out(client, fake_db):
    h = staff(fake_db, "admin", 7)
    assert client.put("/users/7", json={"is_active": False}, headers=h).status_code == 400


def test_security_headers(client):
    r = client.get("/")
    assert r.headers["X-Frame-Options"] == "DENY" and r.headers["X-Content-Type-Options"] == "nosniff"
