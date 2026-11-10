"""Version 2: backup planner, site-survey booking, location, cities, calculator with schedules."""
from datetime import date, timedelta

import pytest
from langchain_core.messages import AIMessage

from app.services import appliances, booking

SID = "c" * 32


@pytest.fixture
def client(fake_db):
    from fastapi.testclient import TestClient
    import main
    fake_db.on("FROM ChatSessions WHERE session_id", lambda p: {"session_id": p[0], "bill_data": None,
                                                              "latest_quote_id": None, "turns": 0, "location": None})
    return TestClient(main.app)


def next_weekday(days=3):
    d = date.today() + timedelta(days=days)
    return d + timedelta(days=1) if d.weekday() == 6 else d


def test_backup_planner_sizes_battery_and_inverter():
    out = appliances.plan([{"name": "ceiling_fan", "quantity": 4}, {"name": "led_light", "quantity": 6},
                           {"name": "fridge", "quantity": 1}], hours_needed=4)
    assert out["running_watts"] == 4 * 80 + 6 * 12 + 200
    assert out["recommended_battery_kwh"] == 5                  # ~2.2 kWh needed -> one 5 kWh pack
    assert out["recommended_inverter_kw"] >= 1
    five = next(h for h in out["hours_per_battery"] if h["battery_kwh"] == 5)
    assert five["hours"] > 4


def test_backup_planner_warns_about_heavy_loads():
    out = appliances.plan([{"name": "ac", "quantity": 3}, {"name": "iron", "quantity": 1}], hours_needed=3)
    assert out["warnings"] and out["recommended_inverter_kw"] >= 6


def test_booking_rules():
    ok = booking.check("Ali Khan", "0300 1234567", "G-11 Islamabad", next_weekday(), "morning")
    assert ok["phone"] == "03001234567"
    for bad in [("A", "03001234567", "G-11", next_weekday(), "morning"),
                ("Ali", "12345", "G-11", next_weekday(), "morning"),
                ("Ali", "03001234567", "G-11", date.today(), "morning"),
                ("Ali", "03001234567", "G-11", date.today() + timedelta(days=60), "morning"),
                ("Ali", "03001234567", "G-11", next_weekday(), "midnight")]:
        with pytest.raises(ValueError):
            booking.check(*bad)


def test_survey_form(client, fake_db):
    body = {"name": "Ali Khan", "phone": "0300-1234567", "area": "Bahria Town Phase 7",
            "preferred_date": str(next_weekday()), "time_slot": "evening", "consent": True}
    r = client.post("/surveys", json=body)
    assert r.status_code == 201, r.text
    assert "4 pm - 7 pm" in r.json()["when"]
    assert fake_db.ran("INSERT INTO SurveyBookings")
    assert client.post("/surveys", json={**body, "consent": False}).status_code == 400
    assert client.post("/surveys", json={**body, "website": "spam"}).status_code == 422      # honeypot


def test_agent_books_a_survey(client, fake_db, scripted):
    from tests.conftest import tool_call
    scripted([tool_call("book_site_survey", {"customer_name": "Sara", "mobile_number": "03211234567",
                                             "area": "DHA 2 Islamabad", "preferred_date": str(next_weekday()),
                                             "time_slot": "afternoon", "customer_agreed": True}),
              AIMessage("Done! The engineer will come in the afternoon.")])
    r = client.post("/chat", json={"session_id": SID, "message": "Yes book it: Sara, 03211234567, DHA 2"})
    assert r.status_code == 200, r.text
    assert r.json()["booking"]["booking_id"] and fake_db.ran("INSERT INTO SurveyBookings")


def test_location_outside_pakistan_is_refused(client, fake_db):
    assert client.post("/chat/location", json={"session_id": SID, "lat": 51.5, "lon": -0.12}).status_code == 400
    r = client.post("/chat/location", json={"session_id": SID, "lat": 33.684, "lon": 73.048})
    assert r.status_code == 200 and r.json()["yearly_kwh_per_kw"] > 1000
    assert fake_db.ran("UPDATE ChatSessions SET location")[0][1][0] == "33.68,73.05"


def test_calculator_understands_a_weekly_schedule(client, fake_db):
    r = client.post("/calculate", json={"monthly_units": [437], "city": "rawalpindi", "outage_days_per_week": 1,
                                        "outage_start_hour": 9, "outage_end_hour": 14, "grid_choice": "no_export"})
    assert r.status_code == 200, r.text
    result = r.json()["result"]
    assert result["inputs"]["outage"]["hours_per_week"] == 5
    assert result["options"]["on_grid"]["main_scenario"] == "no_export"


def test_public_lists(client):
    assert any(c["key"] == "rawalpindi" for c in client.get("/cities").json())
    assert any(a["key"] == "fridge" for a in client.get("/appliances").json())
    sun = client.get("/sunlight?city=lahore").json()
    assert len(sun["monthly_kwh_per_kw"]) == 12
