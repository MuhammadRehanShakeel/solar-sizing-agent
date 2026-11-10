"""
booking.py - "Book a free site survey": checks the details, then saves the booking.

Used by the booking form on the website AND by the agent's book_site_survey tool, so both
follow exactly the same rules. Only the area (sector / town) is stored, never a full address.
"""
import re
from datetime import date, timedelta

from app.services import store

PHONE = re.compile(r"^(?:\+92|0092|0)3\d{9}$")
SLOTS = {"morning": "10 am - 1 pm", "afternoon": "1 pm - 4 pm", "evening": "4 pm - 7 pm"}
MAX_DAYS_AHEAD = 30


def clean_phone(phone: str) -> str:
    return re.sub(r"[\s-]", "", phone or "")


def check(name: str, phone: str, area: str, preferred_date, time_slot: str) -> dict:
    """Returns the cleaned values, or raises ValueError with a message the customer understands."""
    name = " ".join((name or "").split())[:100]
    phone = clean_phone(phone)
    area = " ".join((area or "").split())[:120]
    if len(name) < 2:
        raise ValueError("Please give your name.")
    if not PHONE.match(phone):
        raise ValueError("That mobile number is not valid. A Pakistani mobile looks like 0300 1234567.")
    if len(area) < 3:
        raise ValueError("Please give your area or sector, e.g. 'G-11 Islamabad' or 'Bahria Town Phase 7'.")
    if isinstance(preferred_date, str):
        try:
            preferred_date = date.fromisoformat(preferred_date[:10])
        except ValueError:
            raise ValueError("Please give the date like 2026-11-05.")
    today = date.today()
    if not today + timedelta(days=1) <= preferred_date <= today + timedelta(days=MAX_DAYS_AHEAD):
        raise ValueError(f"Please choose a date between tomorrow and {MAX_DAYS_AHEAD} days from now.")
    if preferred_date.weekday() == 6:
        raise ValueError("Surveys are not done on Sundays. Please choose another day.")
    if time_slot not in SLOTS:
        raise ValueError("Please choose morning, afternoon or evening.")
    return {"name": name, "phone": phone, "area": area, "preferred_date": preferred_date, "time_slot": time_slot}


def book(session_id, quote_id, **details) -> dict:
    data = check(**details)
    booking_id = store.save_booking(session_id, quote_id, data["name"], data["phone"], data["area"],
                                    data["preferred_date"], data["time_slot"])
    when = f"{data['preferred_date']:%A %d %B}, {SLOTS[data['time_slot']]}"
    return {"booking_id": booking_id, "when": when,
            "message": f"Survey requested for {when}. The installer will call {data['phone']} to confirm."}
