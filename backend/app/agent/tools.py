"""
tools.py - The agent's "hands": Python functions the AI is allowed to call.

The AI decides WHEN to call a tool and with WHICH inputs; the tool does the real work
(maths, database) and returns facts. Each tool checks its inputs, because the AI can make mistakes.

make_tools(ctx) builds the tools for ONE chat. `ctx` is a small dict shared with the route:
the tools write the new quote / lead into it, so the web page can show the quote cards.
"""
import re

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.services import booking, sizing, store, tariff
from app.services.prices import get_prices, price_rows

# Typical power of household appliances in Pakistan (watts, while running)
APPLIANCE_WATTS = {
    "fan": 80, "ceiling fan": 80, "dc fan": 35, "inverter fan": 40, "led light": 12, "light": 12, "tube light": 40,
    "energy saver": 25, "fridge": 200, "refrigerator": 200, "freezer": 250, "deep freezer": 250,
    "tv": 100, "led tv": 100, "laptop": 60, "computer": 200, "router": 15, "wifi": 15,
    "ac": 1600, "1 ton ac": 1100, "1.5 ton ac": 1600, "2 ton ac": 2100, "inverter ac": 1000,
    "1.5 ton inverter ac": 1000, "water pump": 750, "motor": 750, "iron": 1000, "washing machine": 500,
    "microwave": 1100, "water dispenser": 500, "electric geyser": 2000, "air cooler": 200, "cooler": 200,
    "phone charger": 10, "ups": 50, "kettle": 1500, "heater": 1500,
}
# Appliances that run on and off by themselves: average share of the time they really draw power
DUTY_CYCLE = {"fridge": 0.45, "refrigerator": 0.45, "freezer": 0.5, "deep freezer": 0.5, "ac": 0.7,
              "1 ton ac": 0.7, "1.5 ton ac": 0.7, "2 ton ac": 0.7, "inverter ac": 0.6, "1.5 ton inverter ac": 0.6}

PHONE = re.compile(r"^(?:\+92|0092|0)3\d{9}$")


class Appliance(BaseModel):
    name: str = Field(description="e.g. 'fan', 'led light', '1.5 ton inverter ac', 'fridge'")
    quantity: int = Field(1, ge=1, le=50)
    hours_per_day: float = Field(8, ge=0, le=24)
    watts: int | None = Field(None, ge=1, le=10000, description="Only if the customer said the wattage")


def appliance_watts(item: Appliance) -> int:
    if item.watts:
        return item.watts
    name = item.name.lower().strip()
    if name in APPLIANCE_WATTS:
        return APPLIANCE_WATTS[name]
    for key in sorted(APPLIANCE_WATTS, key=len, reverse=True):      # "2 ceiling fans" -> "ceiling fan"
        if key in name:
            return APPLIANCE_WATTS[key]
    return 100


def make_tools(ctx: dict):
    """ctx: {"session_id", "quote" (latest saved quote), "lead"} - shared with the chat route."""

    @tool
    def units_from_bill_amount(bill_amount_rs: int, sanctioned_load_kw: float = 5) -> dict:
        """Estimate monthly electricity units from the monthly bill in rupees (when the customer only knows the amount)."""
        if not 200 <= bill_amount_rs <= 3_000_000:
            return {"error": "Bill amount looks wrong; ask the customer again."}
        units = tariff.units_from_bill_amount(bill_amount_rs, sanctioned_load_kw)
        return {"estimated_monthly_units": units,
                "note": "Estimate from the NEPRA 2026 tariff; a bill photo gives a better result."}

    @tool
    def estimate_current_bill(monthly_units: int, sanctioned_load_kw: float = 5, protected: bool = False) -> dict:
        """Estimate the customer's monthly electricity bill (Rs) for a number of units, with the breakdown."""
        if not 1 <= monthly_units <= 50_000:
            return {"error": "Units must be between 1 and 50,000."}
        return tariff.monthly_bill(monthly_units, sanctioned_load_kw, protected)

    @tool
    def estimate_appliance_load(appliances: list[Appliance]) -> dict:
        """Turn a list of appliances into total running watts (for the battery backup) and monthly units."""
        rows, watts, daily_kwh = [], 0, 0.0
        for item in appliances[:30]:
            w = appliance_watts(item)
            duty = DUTY_CYCLE.get(item.name.lower().strip(), 1.0)
            kwh = w * item.quantity * item.hours_per_day * duty / 1000
            rows.append({"name": item.name, "quantity": item.quantity, "watts_each": w,
                         "hours_per_day": item.hours_per_day, "kwh_per_day": round(kwh, 2)})
            watts += w * item.quantity
            daily_kwh += kwh
        return {"appliances": rows, "total_running_watts": watts,
                "units_per_day": round(daily_kwh, 1), "units_per_month": round(daily_kwh * 30)}

    @tool
    def calculate_solar_options(monthly_units: list[int], city: str,
                                outage_hours_per_day: float = 0, outage_days_per_week: int | None = None,
                                outage_start_hour: float | None = None, outage_end_hour: float | None = None,
                                backup_load_watts: int = 1500, roof_area_sqft: int | None = None,
                                budget_rs: int | None = None, sanctioned_load_kw: float | None = None,
                                grid_choice: str = "auto", package: str = "standard") -> dict:
        """Calculate on-grid, hybrid and off-grid systems (size, cost, bill after solar, savings, payback) and save
        a quotation.
        monthly_units: units of the last 1-12 months (or one average value).
        Load-shedding - give what the customer said:
          * a schedule: outage_start_hour + outage_end_hour (24h clock, e.g. 9 and 14 for 9 am-2 pm) and
            outage_days_per_week (e.g. 1 for "once a week"; leave empty for every day), OR
          * only a length: outage_hours_per_day (+ outage_days_per_week if not every day).
          * no load-shedding: leave all at their defaults.
        grid_choice: auto (default) | net_billing (wants green meter) | no_export (stay on WAPDA, no green meter)
                     | off_grid (wants to disconnect WAPDA, or has no connection).
        package: economy | standard | premium."""
        units = [int(u) for u in monthly_units if 0 < int(u) <= 50_000][:12]
        if not units:
            return {"error": "Need the monthly units (1 to 50,000) first."}
        lat, lon = ctx.get("location") or (None, None)
        try:
            result = sizing.calculate_options(
                units, city, outage_hours_per_day, backup_load_watts, roof_area_sqft, budget_rs, sanctioned_load_kw,
                True, prices=get_prices(), outage_days_per_week=outage_days_per_week,
                outage_start_hour=outage_start_hour, outage_end_hour=outage_end_hour, grid_choice=grid_choice,
                tier=package, lat=lat, lon=lon)
        except ValueError as e:
            return {"error": str(e)}
        saved = store.save_quote(ctx.get("session_id"), result)
        ctx["quote"] = {**saved, "result": result}
        return {**sizing.summary(result), "quote_link": saved["url"]}

    @tool
    def book_site_survey(customer_name: str, mobile_number: str, area: str, preferred_date: str, time_slot: str,
                         customer_agreed: bool) -> dict:
        """Book a FREE site survey (an engineer checks the roof, shading and wiring). Only after the customer agreed.
        area: sector / town only (e.g. 'G-11 Islamabad'), never a full address.
        preferred_date: YYYY-MM-DD (tomorrow up to 30 days, not Sunday). time_slot: morning | afternoon | evening."""
        if not customer_agreed:
            return {"error": "Ask the customer for permission first."}
        quote = ctx.get("quote")
        try:
            out = booking.book(ctx.get("session_id"), quote["quote_id"] if quote else None, name=customer_name,
                               phone=mobile_number, area=area, preferred_date=preferred_date, time_slot=time_slot)
        except ValueError as e:
            return {"error": str(e)}
        ctx["booking"] = out
        return out

    @tool
    def get_price_list() -> list:
        """The installer's current prices (panels, inverters, batteries, installation) used in every calculation."""
        return [{"item": r["label"], "price": r["value"], "unit": r["unit"]} for r in price_rows()]

    @tool
    def save_contact(customer_name: str, mobile_number: str, preferred_option: str,
                     customer_agreed: bool) -> dict:
        """Save the customer's name and mobile so the installer calls back. Only after the customer agreed.
        preferred_option: on_grid, hybrid or off_grid."""
        if not customer_agreed:
            return {"error": "Ask the customer for permission first."}
        if not ctx.get("quote"):
            return {"error": "Calculate the solar options first."}
        name = " ".join(customer_name.split())[:100]
        phone = re.sub(r"[\s-]", "", mobile_number)
        if len(name) < 2:
            return {"error": "Ask for the customer's name."}
        if not PHONE.match(phone):
            return {"error": "That mobile number is not valid. A Pakistani mobile looks like 0300 1234567."}
        option = preferred_option if preferred_option in ("on_grid", "hybrid", "off_grid") else \
            ctx["quote"]["result"]["recommended"]
        lead_id = store.save_lead(ctx.get("session_id"), ctx["quote"]["quote_id"], name, phone,
                                  ctx["quote"]["result"]["inputs"]["city"], option)
        ctx["lead"] = {"lead_id": lead_id, "name": name}
        return {"saved": True, "message": "The installer will call within one working day."}

    return [units_from_bill_amount, estimate_current_bill, estimate_appliance_load, calculate_solar_options,
            get_price_list, save_contact, book_site_survey]
