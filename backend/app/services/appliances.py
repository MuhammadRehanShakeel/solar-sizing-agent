"""
appliances.py - The "backup planner": what can my battery run during load-shedding, and for how long?

The customer ticks appliances on the website. We add up the running watts (for the inverter size)
and the energy for the hours they need (for the battery size). Fridges and ACs switch on and off
by themselves, so they use less energy than "watts x hours" (DUTY = share of time really running).
"""
import math

from app.services import sizing

# key: (English, Urdu, watts while running, duty, icon name for the web page)
CATALOGUE = {
    "ceiling_fan": ("Ceiling fan", "پنکھا", 80, 1.0, "fan"),
    "dc_fan": ("DC / inverter fan", "ڈی سی پنکھا", 35, 1.0, "fan"),
    "led_light": ("LED light", "ایل ای ڈی لائٹ", 12, 1.0, "light"),
    "tube_light": ("Tube light", "ٹیوب لائٹ", 40, 1.0, "light"),
    "fridge": ("Fridge", "فریج", 200, 0.45, "fridge"),
    "deep_freezer": ("Deep freezer", "ڈیپ فریزر", 250, 0.5, "fridge"),
    "led_tv": ("LED TV", "ایل ای ڈی ٹی وی", 100, 1.0, "tv"),
    "router": ("WiFi router", "وائی فائی راؤٹر", 15, 1.0, "wifi"),
    "laptop": ("Laptop", "لیپ ٹاپ", 60, 1.0, "laptop"),
    "computer": ("Desktop computer", "کمپیوٹر", 200, 1.0, "computer"),
    "water_motor": ("Water motor (1 hp)", "پانی کی موٹر", 750, 0.3, "water"),
    "inverter_ac": ("Inverter AC 1.5 ton", "انورٹر اے سی", 1000, 0.6, "ac"),
    "ac": ("Normal AC 1.5 ton", "عام اے سی", 1600, 0.7, "ac"),
    "air_cooler": ("Air cooler", "روم کولر", 200, 1.0, "fan"),
    "washing_machine": ("Washing machine", "واشنگ مشین", 500, 0.5, "wash"),
    "iron": ("Iron", "استری", 1000, 0.5, "iron"),
    "microwave": ("Microwave", "مائیکرو ویو", 1100, 0.3, "kitchen"),
    "water_dispenser": ("Water dispenser", "واٹر ڈسپنسر", 500, 0.3, "water"),
    "phone_charger": ("Phone chargers", "موبائل چارجر", 10, 1.0, "phone"),
}
BATTERY_CHOICES = (5, 10, 15, 20)                     # kWh, what installers sell (5 kWh packs)


def catalogue() -> list:
    return [{"key": k, "label": en, "label_ur": ur, "watts": w, "icon": icon}
            for k, (en, ur, w, _, icon) in CATALOGUE.items()]


def plan(items: list, hours_needed: float, battery_pack_kwh: float = 5) -> dict:
    """items: [{"name": key or free text, "quantity": n, "watts": optional}] -> sizes and backup times."""
    rows, running_w, energy_per_hour = [], 0.0, 0.0
    for item in items[:30]:
        key = item["name"] if item["name"] in CATALOGUE else None
        label, _, watts, duty, _ = CATALOGUE[key] if key else (item["name"], "", 100, 1.0, "")
        watts = item.get("watts") or watts
        qty = item.get("quantity", 1)
        rows.append({"name": label, "quantity": qty, "watts_each": watts, "watts_total": watts * qty})
        running_w += watts * qty
        energy_per_hour += watts * qty * duty
    # Starting a motor / compressor needs extra for a moment: inverter = running watts x 1.25 (at least 1 kW).
    inverter_kw = sizing._inverter_for(max(1.0, running_w * 1.25 / 1000) / sizing.DC_AC_RATIO)
    needed_kwh = energy_per_hour / 1000 * hours_needed
    usable = sizing.BATTERY_DOD * sizing.BATTERY_EFFICIENCY
    packs = max(1, math.ceil(needed_kwh / usable / battery_pack_kwh - 1e-9))
    hours_per_battery = [{"battery_kwh": b, "hours": round(b * usable / (energy_per_hour / 1000), 1)
                          if energy_per_hour else None} for b in BATTERY_CHOICES]
    warnings = []
    if running_w > 5000:
        warnings.append("This is a lot to run on a battery at once. Leave ACs and irons for when WAPDA is on.")
    return {"appliances": rows, "running_watts": round(running_w), "energy_per_hour_wh": round(energy_per_hour),
            "hours_needed": hours_needed, "battery_needed_kwh": round(needed_kwh, 1),
            "recommended_battery_kwh": packs * battery_pack_kwh, "recommended_inverter_kw": inverter_kw,
            "hours_per_battery": hours_per_battery, "warnings": warnings}
