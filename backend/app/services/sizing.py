"""
sizing.py - The solar calculator. Plain Python maths, NO AI.

Why no AI here? Language models are bad at arithmetic and sometimes invent numbers.
So the agent never calculates by itself: it calls calculate_options(), and this file
gives the same answer every time for the same inputs (easy to test and to explain).

Three systems are always worked out:
  on_grid   panels + on-grid inverter. Cheapest. Switches OFF during load-shedding (safety rule).
  hybrid    panels + hybrid inverter + lithium battery. Runs the house in load-shedding.
  off_grid  bigger panels + bigger battery, can work with NO WAPDA connection at all.

And for each system, the bill in every situation the customer may choose:
  net_billing   connected to WAPDA with a green meter: exports earn ~Rs 11/unit
  no_export     connected to WAPDA, no green meter: extra solar is simply not used
  disconnected  (off-grid) WAPDA meter removed: no bill at all
  wapda_backup  (off-grid) WAPDA kept only for days the sun is not enough: pay only for those units
"""
import math

from app.services import sunlight, tariff

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = sunlight.DAYS
INVERTER_SIZES = [3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50]   # kW, what the market sells
DC_AC_RATIO = 1.2                    # panels may be up to 20 % bigger than the inverter
BATTERY_DOD = 0.9                    # use 90 % of a lithium battery
BATTERY_EFFICIENCY = 0.92            # energy lost charging + discharging
GRID_CO2_KG_PER_KWH = 0.45           # Pakistan grid emission factor (approx.)
SQFT_PER_M2 = 10.764
SUN_HOURS = 9                        # 8 am - 5 pm

# Packages: how the price and the parts change. Prices are % of "standard" (set on the Prices page).
TIERS = {
    "economy": {"label": "Economy", "parts": "Tier-1 P-type / budget N-type panels, local-brand inverter, "
                "locally assembled LiFePO4 battery", "warranty": "Panels 10 yr, inverter 1-2 yr, battery 3 yr"},
    "standard": {"label": "Standard", "parts": "Tier-1 N-type TOPCon panels (e.g. JA, Jinko, Longi), "
                 "Growatt / Solis / Deye class inverter, LiFePO4 6000-cycle battery",
                 "warranty": "Panels 12 yr (30 yr output), inverter 5 yr, battery 5 yr"},
    "premium": {"label": "Premium", "parts": "Top N-type / HJT panels, Huawei / Fronius class inverter, "
                "branded battery with app monitoring", "warranty": "Panels 15 yr (30 yr output), inverter 10 yr, "
                "battery 10 yr"},
}


# ---------------------------------------------------------------------------
# Load-shedding: "2 hours a day" or "once a week, 9 am to 2 pm"
# ---------------------------------------------------------------------------
def _overlap(start: float, end: float, a: float, b: float) -> float:
    """Hours of [start, end) (may pass midnight) that fall inside [a, b)."""
    total, hour = 0.0, start
    length = (end - start) % 24 or 24
    steps = int(length * 4)
    for i in range(steps):                                 # 15-minute steps: simple and exact enough
        h = (start + i * 0.25) % 24
        if a <= h < b:
            total += 0.25
    return total


def outage_profile(hours_per_day=0.0, days_per_week=None, start_hour=None, end_hour=None, daylight=(8, 17)):
    """
    Describe load-shedding in one way, whatever the customer said.
      hours_per_day only            -> every day, timing unknown (we assume half in daylight)
      start_hour + end_hour (+days) -> exact window, e.g. 9 -> 14 on 1 day a week
    """
    if start_hour is not None and end_hour is not None:
        start, end = float(start_hour) % 24, float(end_hour) % 24
        hours = (end - start) % 24 or 24.0
        days = 7 if days_per_week is None else max(0, min(7, int(days_per_week)))
        day_hours = _overlap(start, end, *daylight)
        timing_known = True
    else:
        hours = max(0.0, min(24.0, float(hours_per_day or 0)))
        days = 7 if hours else 0
        if days_per_week is not None and hours:
            days = max(0, min(7, int(days_per_week)))
        day_hours = hours / 2
        start = end = None
        timing_known = False
    if not days or not hours:
        return {"days_per_week": 0, "hours_per_cut": 0, "daylight_hours": 0, "dark_hours": 0,
                "hours_per_week": 0, "average_hours_per_day": 0, "start_hour": None, "end_hour": None,
                "timing_known": timing_known, "text": "No load-shedding"}
    when = f"{_clock(start)}-{_clock(end)}" if timing_known else "time not given"
    text = f"{'every day' if days == 7 else f'{days} day' + ('s' if days != 1 else '') + ' a week'}, {when} ({hours:g} h)"
    return {"days_per_week": days, "hours_per_cut": round(hours, 2), "daylight_hours": round(day_hours, 2),
            "dark_hours": round(hours - day_hours, 2), "hours_per_week": round(hours * days, 1),
            "average_hours_per_day": round(hours * days / 7, 2), "start_hour": start, "end_hour": end,
            "timing_known": timing_known, "text": text}


def _clock(h):
    h = float(h) % 24
    suffix = "am" if h < 12 else "pm"
    hour = int(h) % 12 or 12
    minutes = int(round((h - int(h)) * 60))
    return f"{hour}{':%02d' % minutes if minutes else ''} {suffix}"


# ---------------------------------------------------------------------------
# Sizes and prices
# ---------------------------------------------------------------------------
def monthly_profile(monthly_units) -> list:
    """12 months of usage. With fewer than 12 bill months we repeat the average."""
    values = [max(0.0, float(u)) for u in (monthly_units or []) if u is not None]
    if not values:
        raise ValueError("At least one month of electricity units is needed.")
    if len(values) >= 12:
        return values[-12:]
    average = sum(values) / len(values)
    return [average] * 12


def _inverter_for(kw: float) -> int:
    for size in INVERTER_SIZES:
        if size * DC_AC_RATIO >= kw:
            return size
    return INVERTER_SIZES[-1]


def _panels_for(kw: float, prices: dict) -> int:
    return max(2, math.ceil(kw * 1000 / prices["panel_watt"]))


def _battery_kwh(needed_kwh: float, prices: dict) -> float:
    pack = prices["battery_pack_kwh"]
    packs = max(1, math.ceil(needed_kwh / BATTERY_DOD / BATTERY_EFFICIENCY / pack - 1e-9))
    return packs * pack


def tier_factor(tier: str, prices: dict) -> float:
    return {"economy": prices["economy_percent"] / 100, "premium": prices["premium_percent"] / 100}.get(tier, 1.0)


def _costs(kind: str, panels: int, inverter_kw: int, battery_kwh: float, prices: dict, tier="standard") -> dict:
    kw = panels * prices["panel_watt"] / 1000
    factor = tier_factor(tier, prices)
    items = {
        "panels": panels * prices["panel_watt"] * prices["panel_price_per_watt"] * factor,
        "inverter": (prices["ongrid_inverter_base"] + prices["ongrid_inverter_per_kw"] * inverter_kw
                     if kind == "on_grid" else
                     prices["hybrid_inverter_base"] + prices["hybrid_inverter_per_kw"] * inverter_kw) * factor,
        "batteries": battery_kwh * prices["battery_per_kwh"] * factor,
        "structure": kw * prices["structure_per_kw"],
        "installation": prices["installation_base"] + kw * prices["installation_per_kw"],
        "net_billing": prices["net_billing_fee"] if kind != "off_grid" else 0,
    }
    subtotal = sum(items.values())
    items["margin"] = subtotal * prices["margin_percent"] / 100
    items = {k: round(v) for k, v in items.items()}
    return {"items": items, "total": sum(items.values())}


def instalment(principal: float, months: int, yearly_rate_percent: float) -> int:
    """Equal monthly instalment (like a bank loan). 0 % markup -> simply principal / months."""
    r = yearly_rate_percent / 100 / 12
    if r <= 0:
        return round(principal / months)
    return round(principal * r / (1 - (1 + r) ** -months))


def financing(total: float, monthly_saving: float, prices: dict, months_options=(12, 24, 36)) -> dict:
    down = round(total * prices["down_payment_percent"] / 100)
    plans = []
    for months in months_options:
        monthly = instalment(total - down, months, prices["finance_rate"])
        plans.append({"months": months, "monthly": monthly, "total_paid": down + monthly * months,
                      "covered_by_saving_percent": round(100 * monthly_saving / monthly) if monthly else 100})
    return {"down_payment": down, "markup_percent": prices["finance_rate"], "plans": plans,
            "note": "Example plan. Real bank / installer financing terms differ."}


# ---------------------------------------------------------------------------
# Month-by-month simulation
# ---------------------------------------------------------------------------
def _simulate(kind, kw, battery_kwh, usage, day_share, yields, sanctioned_kw, prices, outage):
    """How much the panels make, use directly, store, export and import - and the bill in each situation."""
    export_rate = prices["export_rate"]
    # On-grid inverters must switch off when WAPDA is off (to protect line workers), so the
    # sunshine during daytime load-shedding is lost. Hybrid / off-grid keep working.
    lost_share = 0.0
    if kind == "on_grid" and outage["days_per_week"]:
        lost_share = outage["days_per_week"] / 7 * outage["daylight_hours"] / SUN_HOURS
    months = []
    for m, used in enumerate(usage):
        days = DAYS[m]
        generated = kw * yields[m] * (1 - min(0.9, lost_share))
        daytime_need = used * day_share
        direct = min(generated, daytime_need)
        spare = generated - direct
        stored = 0.0
        if battery_kwh:
            night_need = used - direct
            stored = min(spare * BATTERY_EFFICIENCY, battery_kwh * BATTERY_DOD * days, night_need)
            spare -= stored / BATTERY_EFFICIENCY
        self_used = direct + stored
        short = max(0.0, used - self_used)                     # what the sun + battery could not supply
        bill_before = tariff.monthly_bill(used, sanctioned_kw)["total"]
        if kind == "off_grid":
            bills = {"disconnected": 0,
                     "wapda_backup": tariff.monthly_bill(short, sanctioned_kw)["total"] if short >= 1 else
                     tariff.monthly_bill(0, sanctioned_kw)["total"]}
            imported, exported = short, 0.0
        else:
            bills = {"net_billing": tariff.bill_with_solar(short, spare, sanctioned_kw, export_rate)["payable"],
                     "no_export": tariff.monthly_bill(short, sanctioned_kw)["total"]}
            imported, exported = short, spare
        months.append({"month": MONTHS[m], "used": round(used), "generated": round(generated),
                       "self_used": round(self_used), "imported": round(imported), "exported": round(exported),
                       "solar_share_percent": round(100 * self_used / used) if used else 100,
                       "bill_before": bill_before, "bills": bills})
    return months


SCENARIO_LABELS = {
    "net_billing": "Connected to WAPDA with net billing (green meter)",
    "no_export": "Connected to WAPDA, no net billing (extra solar not sold)",
    "disconnected": "WAPDA disconnected - fully independent",
    "wapda_backup": "WAPDA kept only as backup (no net billing)",
}


def _scenarios(months, cost_total, kind):
    out = []
    for key in (("disconnected", "wapda_backup") if kind == "off_grid" else ("net_billing", "no_export")):
        yearly_after = sum(m["bills"][key] for m in months)
        yearly_saving = sum(m["bill_before"] for m in months) - yearly_after
        out.append({"key": key, "label": SCENARIO_LABELS[key], "monthly_bill": round(yearly_after / 12),
                    "monthly_saving": round(yearly_saving / 12), "yearly_saving": round(yearly_saving),
                    "payback_years": round(cost_total / yearly_saving, 1) if yearly_saving > 0 else None})
    return out


# ---------------------------------------------------------------------------
# The main function
# ---------------------------------------------------------------------------
def calculate_options(monthly_units, city="islamabad", outage_hours=0.0, backup_load_w=1500,
                      roof_area_sqft=None, budget_rs=None, sanctioned_load_kw=None, has_grid=True,
                      daytime_share=0.45, prices=None, outage_days_per_week=None, outage_start_hour=None,
                      outage_end_hour=None, grid_choice="auto", tier="standard", lat=None, lon=None,
                      solar=None) -> dict:
    """
    Returns the three systems with sizes, costs, the bill in every situation, savings and payback,
    plus which one we recommend and why. All numbers are rounded for showing to customers.

    grid_choice: auto | net_billing | no_export | off_grid  (what the customer wants to do with WAPDA)
    solar      : sunlight.solar_yield(...) result; looked up here when not given (tests pass it in)
    """
    from app.services.prices import defaults
    prices = {**defaults(), **(prices or {})}
    tier = tier if tier in TIERS else "standard"
    grid_choice = grid_choice if grid_choice in ("auto", "net_billing", "no_export", "off_grid") else "auto"
    if not has_grid:
        grid_choice = "off_grid"
    usage = monthly_profile(monthly_units)
    yearly_units = sum(usage)
    average = yearly_units / 12
    solar = solar or sunlight.solar_yield(city, lat, lon)
    yields = solar["monthly_kwh_per_kw"]
    yearly_yield = sum(yields)
    sanctioned = float(sanctioned_load_kw or max(3, math.ceil(average / 100)))
    daytime_share = min(0.8, max(0.2, float(daytime_share)))
    backup_load_w = max(300.0, min(20000.0, float(backup_load_w or 1500)))
    backup_kw = backup_load_w / 1000
    outage = outage_profile(outage_hours, outage_days_per_week, outage_start_hour, outage_end_hour)

    # 1. Panels: make about as much as the house uses in a year. With net billing an export earns only
    #    ~Rs 11, so making MORE than you use rarely pays back.
    target_kw = yearly_units / yearly_yield
    notes = []
    max_panels = None
    if roof_area_sqft:
        max_panels = int(float(roof_area_sqft) / SQFT_PER_M2 // prices["panel_area_m2"])
        if max_panels < 2:
            raise ValueError("The roof is too small for a solar system (need at least ~70 sq ft).")

    def fit(kw):
        panels = _panels_for(kw, prices)
        if max_panels and panels > max_panels:
            notes.append(f"Your roof fits at most {max_panels} panels, so the system is limited to that.")
            panels = max_panels
        return panels

    # Battery for the hybrid: enough for the dark part of the longest cut + a small margin for the
    # daylight part (clouds, early morning). At least one pack, which also stores sun for the evening.
    hybrid_need = backup_kw * (outage["dark_hours"] + 0.25 * outage["daylight_hours"])
    # Off-grid: panels for the WORST month (winter), battery for one evening + night.
    worst = max(u / y for u, y in zip(usage, yields) if y)
    night_kwh = average * (1 - daytime_share) / 30.4

    results = {}
    for kind in ("on_grid", "hybrid", "off_grid"):
        if kind == "off_grid":
            kw_needed = min(worst * 0.95, target_kw * 2)
            battery = _battery_kwh(night_kwh * 1.2, prices)
        elif kind == "hybrid":
            kw_needed = target_kw
            battery = _battery_kwh(hybrid_need, prices)
        else:
            kw_needed, battery = target_kw, 0.0
        panels = fit(kw_needed)
        kw = round(panels * prices["panel_watt"] / 1000, 2)
        inverter = _inverter_for(kw)
        if kind != "on_grid":
            inverter = max(inverter, _inverter_for(backup_kw * 1.25))
        cost = _costs(kind, panels, inverter, battery, prices, tier)
        months = _simulate(kind, kw, battery, usage, daytime_share, yields, sanctioned, prices, outage)
        scenarios = _scenarios(months, cost["total"], kind)
        main = scenarios[0]
        if kind != "off_grid" and grid_choice == "no_export":
            main = scenarios[1]
        generated = sum(m["generated"] for m in months)
        self_used = sum(m["self_used"] for m in months)
        backup_hours = round(battery * BATTERY_DOD / backup_kw, 1) if battery else 0
        results[kind] = {
            "kind": kind,
            "system_kw": kw, "panels": panels, "panel_watt": int(prices["panel_watt"]),
            "inverter_kw": inverter, "battery_kwh": battery, "backup_hours": backup_hours,
            "roof_sqft": round(panels * prices["panel_area_m2"] * SQFT_PER_M2),
            "cost": cost,
            "yearly_generation": round(generated),
            "scenarios": scenarios,
            "main_scenario": main["key"],
            "monthly_bill_after": main["monthly_bill"],
            "yearly_saving": main["yearly_saving"],
            "monthly_saving": main["monthly_saving"],
            "payback_years": main["payback_years"],
            "saving_25_years": round(main["yearly_saving"] * sum(0.995 ** y for y in range(25))),
            "co2_tonnes_per_year": round(min(generated, yearly_units) * GRID_CO2_KG_PER_KWH / 1000, 1),
            "self_use_percent": round(100 * self_used / max(1, generated)),
            "solar_covers_percent": round(100 * self_used / yearly_units) if yearly_units else 100,
            "short_months": [m["month"] for m in months if m["solar_share_percent"] < 90] if kind == "off_grid" else [],
            "works_in_load_shedding": kind != "on_grid",
            "months": months,
            "over_budget": bool(budget_rs and cost["total"] > float(budget_rs)),
        }

    # 2. Recommend one, with a reason the customer understands.
    weekly = outage["hours_per_week"]
    if grid_choice == "off_grid":
        pick = "off_grid"
        reason = ("There is no WAPDA connection, so only an off-grid system can work." if not has_grid else
                  "You want to be fully independent of WAPDA, so the off-grid system is sized for winter.")
    elif weekly >= 7 or (outage["dark_hours"] >= 2 and outage["days_per_week"] >= 3):
        pick = "hybrid"
        reason = (f"Load-shedding ({outage['text']}) is enough that a battery is worth it: the hybrid keeps "
                  f"your essential load ({backup_kw:g} kW) running, and uses the sun directly during daytime cuts.")
    else:
        pick = "on_grid"
        reason = ("Load-shedding is rare, so the cheapest system with the fastest payback is best."
                  if not weekly else
                  f"Load-shedding is short ({outage['text']}), so the cheaper on-grid system pays back fastest. "
                  f"Note: on-grid switches off during cuts; choose hybrid if you need power then.")
    if budget_rs and results[pick]["over_budget"] and not results["on_grid"]["over_budget"] and pick != "on_grid" \
            and grid_choice != "off_grid":
        reason += " It is above your budget, so the on-grid system is the budget choice."
    if outage["days_per_week"] and outage["daylight_hours"] and pick != "on_grid":
        notes.append("During daytime load-shedding an on-grid system stops working (safety rule); "
                     "the hybrid keeps running straight from the panels.")
    if not outage["timing_known"] and outage["days_per_week"]:
        notes.append("Load-shedding time not given: we assumed half of it is after sunset.")
    if sanctioned < results["on_grid"]["system_kw"] / DC_AC_RATIO:
        notes.append(f"Your sanctioned load ({sanctioned:g} kW) is smaller than the system; the DISCO may ask "
                     f"you to increase it before approving net billing.")
    if results["off_grid"]["short_months"]:
        notes.append("Off-grid: in " + ", ".join(results["off_grid"]["short_months"]) + " the sun alone may not "
                     "cover everything on cloudy days - keep WAPDA or a generator as backup, or use less.")

    chosen = results[pick]
    packages = []
    for t in ("economy", "standard", "premium"):
        cost = _costs(pick, chosen["panels"], chosen["inverter_kw"], chosen["battery_kwh"], prices, t)
        packages.append({"tier": t, **TIERS[t], "total": cost["total"],
                         "payback_years": round(cost["total"] / chosen["yearly_saving"], 1)
                         if chosen["yearly_saving"] > 0 else None})

    current_bill = tariff.monthly_bill(average, sanctioned)
    return {
        "inputs": {"monthly_units": [round(u) for u in usage], "average_units": round(average),
                   "city": sunlight.city_key(city), "outage": outage, "outage_hours": outage["average_hours_per_day"],
                   "backup_load_w": backup_load_w, "roof_area_sqft": roof_area_sqft, "budget_rs": budget_rs,
                   "sanctioned_load_kw": sanctioned, "has_grid": has_grid, "grid_choice": grid_choice,
                   "tier": tier, "daytime_share": daytime_share},
        "current_bill": current_bill,
        "yearly_bill": sum(m["bill_before"] for m in results["on_grid"]["months"]),
        "options": results,
        "recommended": pick,
        "reason": reason,
        "notes": list(dict.fromkeys(notes)),
        "packages": packages,
        "financing": financing(chosen["cost"]["total"], chosen["monthly_saving"], prices),
        "sunlight": {k: solar[k] for k in ("source", "yearly_kwh_per_kw", "monthly_kwh_per_kw", "nasa")},
        "assumptions": {
            "yield_kwh_per_kw_year": round(yearly_yield), "sunlight_source": solar["source"],
            "export_rate": prices["export_rate"], "panel_price_per_watt": prices["panel_price_per_watt"],
            "battery_per_kwh": prices["battery_per_kwh"], "daytime_use_percent": round(daytime_share * 100),
            "tariff": "NEPRA domestic schedule S.R.O. 279(I)/2026, non-protected, without FPA/QTA",
            "net_billing": "Net billing for new solar users since 9 Feb 2026 (S.R.O. 251(I)/2026)",
        },
    }


def summary(result: dict) -> dict:
    """Short version for the AI (fewer tokens): no month-by-month tables."""
    out = {"recommended": result["recommended"], "reason": result["reason"], "notes": result["notes"],
           "current_monthly_bill_rs": result["current_bill"]["total"],
           "average_units": result["inputs"]["average_units"],
           "load_shedding": result["inputs"]["outage"]["text"],
           "sunlight": result["sunlight"]["source"]}
    for kind, o in result["options"].items():
        out[kind] = {k: o[k] for k in ("system_kw", "panels", "inverter_kw", "battery_kwh", "backup_hours",
                                       "monthly_saving", "payback_years", "monthly_bill_after", "over_budget",
                                       "works_in_load_shedding", "solar_covers_percent")}
        out[kind]["total_cost_rs"] = o["cost"]["total"]
        out[kind]["bill_by_situation"] = {s["label"]: s["monthly_bill"] for s in o["scenarios"]}
    out["packages"] = {p["label"]: p["total"] for p in result["packages"]}
    first = result["financing"]["plans"][1]
    out["example_instalment"] = (f"{first['months']} months: Rs {first['monthly']:,}/month after "
                                 f"Rs {result['financing']['down_payment']:,} down payment")
    return out
