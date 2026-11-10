"""
demo_data.py - Puts realistic DEMO customers in the database, so the installer pages are not empty
in screenshots and demos.

    backend\\venv\\Scripts\\python.exe scripts\\demo_data.py           add / refresh the demo data
    backend\\venv\\Scripts\\python.exe scripts\\demo_data.py --remove  delete it again

Safe to run again: it deletes its own demo rows first and never touches real customers (every demo
session_id starts with "demo"). It also makes a demo staff account with a NEW random password and
writes it to DEMO_ACCOUNT.txt (git-ignored), so screenshots never need your own password.
"""
import json
import os
import secrets
import sys
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))

from app.core.security import hash_password  # noqa: E402
from app.database import execute_insert_and_get_id, execute_query  # noqa: E402
from app.services import sizing  # noqa: E402
from app.services.prices import defaults  # noqa: E402

DEMO_EMAIL = "demo.sales@solarsaathi.pk"

# Each demo customer: the chat, what they wanted, and what happened afterwards.
CUSTOMERS = [
    {
        "name": "Bilal Ahmed", "phone": "03005551234", "city": "rawalpindi", "units": [437] * 12,
        "outage": {"outage_days_per_week": 1, "outage_start_hour": 9, "outage_end_hour": 14},
        "backup": 800, "grid": "auto", "status": "won", "note": "Installed 15 Oct. Paid in 2 instalments.",
        "chat": [
            ("user", "Assalam o alaikum. Bill 25 hazar aata hai, Rawalpindi mein ghar hai."),
            ("assistant", "Wa alaikum assalam! Rs 25,000 ka bill matlab takreeban 437 units. Load-shedding kitni "
                          "hoti hai aur kis waqt?", "estimate_current_bill"),
            ("user", "Hafte mein ek dafa, 9 se 2 baje tak."),
            ("assistant", "Ye din ka waqt hai, to panels khud ghar chala lenge. **{name} {kw} kW** ({panels} panels) "
                          "Rs {cost}, bill Rs {before} se Rs {after} reh jayega, {payback} saal mein paisay poore.",
             "calculate_solar_options"),
            ("user", "Theek hai, call kar lein. Bilal Ahmed, 0300 5551234"),
            ("assistant", "Shukriya Bilal sahab! Hamari team aaj hi call karegi.", "save_contact"),
        ],
    },
    {
        "name": "Sara Khan", "phone": "03211234567", "city": "islamabad", "units": [620] * 12,
        "outage": {"outage_start_hour": 19, "outage_end_hour": 22}, "backup": 2500, "grid": "auto",
        "status": "site_visit", "note": "Survey booked. Roof is shaded after 4 pm - check.",
        "survey": {"area": "DHA Phase 2, Islamabad", "days": 3, "slot": "afternoon", "status": "confirmed"},
        "chat": [
            ("user", "We use about 620 units a month in Islamabad. Light goes 7 to 10 every night."),
            ("assistant", "Night load-shedding needs a battery. What must keep running - fans and lights only, "
                          "or the fridge and an AC too?", None),
            ("user", "Fans, lights, fridge and one inverter AC."),
            ("assistant", "That is about 2.5 kW. **{name} {kw} kW with a {battery} kWh battery** keeps all of it "
                          "running through the 3-hour cut. Rs {cost}, your bill drops from Rs {before} to about "
                          "Rs {after}, payback {payback} years.", "estimate_appliance_load, calculate_solar_options"),
            ("user", "Can someone come and see the roof?"),
            ("assistant", "Done - a free site survey is booked. The engineer will call to confirm.",
             "book_site_survey"),
        ],
    },
    {
        "name": "Imran Malik", "phone": "03339876543", "city": "lahore", "units": [310] * 12,
        "outage": {"outage_hours": 0}, "backup": 1500, "grid": "off_grid", "status": "contacted",
        "note": "Wants to leave WAPDA completely. Warned about winter months.",
        "chat": [
            ("user", "I want to remove my WAPDA meter completely. 310 units, Lahore."),
            ("assistant", "Fully off-grid is possible: **{kw} kW with a {battery} kWh battery**, Rs {cost}, and no "
                          "bill at all. But in December and January fog can cut the sun by a third - on cloudy days "
                          "you may need to use less, or keep WAPDA only as a backup.", "calculate_solar_options"),
            ("user", "Ok send me the quote"),
            ("assistant", "Here is the full quotation with both options and the month-by-month chart.", None),
        ],
    },
    {
        "name": "Ayesha Siddiqui", "phone": "03451112233", "city": "faisalabad", "units": [890] * 12,
        "outage": {"outage_days_per_week": 4, "outage_start_hour": 13, "outage_end_hour": 16},
        "backup": 4000, "grid": "net_billing", "status": "new", "note": None,
        "survey": {"area": "Madina Town, Faisalabad", "days": 5, "slot": "morning", "status": "requested"},
        "chat": [
            ("user", "Bill 55,000. Faisalabad. Light 4 din hafte mein, 1 se 4 baje."),
            ("assistant", "Din ke waqt ki load-shedding hai, to hybrid system panels se seedha ghar chalayega. "
                          "**{name} {kw} kW, {battery} kWh battery**, Rs {cost}, bill Rs {before} se Rs {after}, "
                          "payback {payback} saal.", "units_from_bill_amount, calculate_solar_options"),
        ],
    },
    {
        "name": "Hassan Raza", "phone": "03017778899", "city": "multan", "units": [150] * 12,
        "outage": {"outage_hours": 2}, "backup": 800, "grid": "auto", "status": "lost",
        "note": "Budget too small for now. Call again in 6 months.",
        "chat": [
            ("user", "Chota ghar hai, 150 units. Budget 3 lakh."),
            ("assistant", "150 units ke liye **{name} {kw} kW** ({panels} panels) kafi hai, Rs {cost}. "
                          "Bill Rs {before} se Rs {after} reh jayega.", "calculate_solar_options"),
        ],
    },
]


def remove():
    execute_query("DELETE FROM SurveyBookings WHERE session_id LIKE 'demo%'", commit=True)
    execute_query("UPDATE ChatSessions SET latest_quote_id = NULL WHERE session_id LIKE 'demo%'", commit=True)
    execute_query("DELETE FROM Leads WHERE session_id LIKE 'demo%'", commit=True)
    execute_query("DELETE FROM Quotes WHERE session_id LIKE 'demo%'", commit=True)
    execute_query("DELETE FROM ChatMessages WHERE session_id LIKE 'demo%'", commit=True)
    execute_query("DELETE FROM ChatSessions WHERE session_id LIKE 'demo%'", commit=True)


def demo_staff() -> str:
    """Make (or reset) the demo staff account and return its new password."""
    password = "Demo-" + secrets.token_urlsafe(9) + "4"
    row = execute_query("SELECT user_id FROM Users WHERE email = ?", (DEMO_EMAIL,), fetch_one=True)
    if row:
        execute_query("UPDATE Users SET password_hash = ?, is_active = 1, failed_logins = 0, locked_until = NULL "
                      "WHERE user_id = ?", (hash_password(password), row["user_id"]), commit=True)
    else:
        execute_query("INSERT INTO Users (full_name, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                      ("Demo Sales Manager", DEMO_EMAIL, hash_password(password)), commit=True)
    with open(os.path.join(ROOT, "DEMO_ACCOUNT.txt"), "w", encoding="utf-8") as f:
        f.write("# Demo staff account for screenshots. Git-ignored. Delete this file when you are done.\n"
                f"admin_email={DEMO_EMAIL}\nadmin_password={password}\n")
    return password


NAMES = {"on_grid": "On-grid", "hybrid": "Hybrid", "off_grid": "Off-grid"}


def facts(result):
    """The numbers the demo chat quotes - taken from the real calculation, so they always match."""
    best = result["options"][result["recommended"]]
    return {"name": NAMES[result["recommended"]], "kw": best["system_kw"], "panels": best["panels"],
            "battery": best["battery_kwh"], "cost": f"{best['cost']['total']:,}",
            "before": f"{result['current_bill']['total']:,}", "after": f"{best['monthly_bill_after']:,}",
            "saving": f"{best['monthly_saving']:,}", "payback": best["payback_years"]}


def add():
    prices = defaults()
    for i, c in enumerate(CUSTOMERS, start=1):
        session_id = f"demo{i:028d}"
        result = sizing.calculate_options(c["units"], c["city"], backup_load_w=c["backup"], prices=prices,
                                          grid_choice=c["grid"], **c["outage"])
        best = result["options"][result["recommended"]]
        numbers = facts(result)
        execute_query("INSERT INTO ChatSessions (session_id, turns) VALUES (?, ?)",
                      (session_id, len([m for m in c["chat"] if m[0] == "user"])), commit=True)
        for message in c["chat"]:
            role, content = message[0], message[1].format(**numbers)
            tools = message[2] if len(message) > 2 else None
            execute_query("INSERT INTO ChatMessages (session_id, role, content, model, tools_used) "
                          "VALUES (?, ?, ?, ?, ?)",
                          (session_id, role, content, "groq:openai/gpt-oss-120b" if role == "assistant" else None,
                           tools), commit=True)
        quote_id = execute_insert_and_get_id(
            "INSERT INTO Quotes (session_id, public_token, city, average_units, recommended, recommended_kw, "
            "recommended_cost, result_json) OUTPUT INSERTED.quote_id VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, secrets.token_hex(16), c["city"], result["inputs"]["average_units"], result["recommended"],
             best["system_kw"], best["cost"]["total"], json.dumps(result)))
        execute_query("UPDATE ChatSessions SET latest_quote_id = ? WHERE session_id = ?", (quote_id, session_id),
                      commit=True)
        execute_query("INSERT INTO Leads (session_id, quote_id, customer_name, phone, city, preferred_option, "
                      "status, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                      (session_id, quote_id, c["name"], c["phone"], c["city"], result["recommended"], c["status"],
                       c["note"]), commit=True)
        survey = c.get("survey")
        if survey:
            when = date.today() + timedelta(days=survey["days"])
            if when.weekday() == 6:
                when += timedelta(days=1)
            execute_query("INSERT INTO SurveyBookings (session_id, quote_id, customer_name, phone, area, "
                          "preferred_date, time_slot, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          (session_id, quote_id, c["name"], c["phone"], survey["area"], when, survey["slot"],
                           survey["status"]), commit=True)
        print(f"  {c['name']:20s} {result['recommended']:9s} {best['system_kw']:>5} kW  Rs {best['cost']['total']:,}")


def main():
    remove()
    if "--remove" in sys.argv:
        print("Demo data removed.")
        return
    print("Adding demo customers:")
    add()
    demo_staff()
    print(f"\nDemo staff account written to DEMO_ACCOUNT.txt (email {DEMO_EMAIL}).")
    print("Done. Refresh the installer pages to see them.")


if __name__ == "__main__":
    main()
