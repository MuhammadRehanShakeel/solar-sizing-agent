"""The calculator and the bill maths: plain Python, so every number can be checked exactly."""
import pytest

from app.services import sizing, tariff


def test_non_protected_bill_uses_one_rate_for_every_unit():
    bill = tariff.monthly_bill(300, sanctioned_load_kw=5)
    assert bill["energy"] == round(300 * 33.10)
    assert bill["fixed"] == 350 * 5
    assert bill["total"] > bill["energy"]


def test_protected_customer_pays_progressive_cheaper_slabs():
    protected = tariff.monthly_bill(150, protected=True)
    assert protected["energy"] == round(100 * 10.54 + 50 * 13.01)
    assert protected["total"] < tariff.monthly_bill(150)["total"]
    assert tariff.monthly_bill(250, protected=True)["protected"] is False     # above 200 units: no protection


def test_units_from_bill_amount_is_the_inverse_of_the_bill():
    for units in (120, 350, 800):
        amount = tariff.monthly_bill(units)["total"]
        assert abs(tariff.units_from_bill_amount(amount) - units) <= 1


def test_net_billing_credit_never_removes_fixed_charges():
    out = tariff.bill_with_solar(import_units=10, export_units=2000)
    assert out["payable"] >= tariff.monthly_bill(10)["fixed"]


def test_on_grid_makes_about_what_the_house_uses():
    r = sizing.calculate_options([500] * 12, "islamabad")
    on = r["options"]["on_grid"]
    assert 0.95 <= on["yearly_generation"] / 6000 <= 1.15
    assert on["battery_kwh"] == 0 and r["options"]["hybrid"]["battery_kwh"] >= 5
    assert r["recommended"] == "on_grid"
    assert on["payback_years"] and 1 < on["payback_years"] < 10


def test_costs_add_up():
    on = sizing.calculate_options([400], "lahore")["options"]["on_grid"]
    assert sum(on["cost"]["items"].values()) == on["cost"]["total"]


def test_load_shedding_recommends_hybrid_and_battery_covers_the_hours():
    r = sizing.calculate_options([500], "rawalpindi", outage_hours=4, backup_load_w=2000)
    assert r["recommended"] == "hybrid"
    assert r["options"]["hybrid"]["backup_hours"] >= 4
    assert "load-shedding" in r["reason"].lower()


def test_no_grid_recommends_off_grid():
    r = sizing.calculate_options([300], "quetta", has_grid=False)
    assert r["recommended"] == "off_grid"
    assert r["options"]["off_grid"]["system_kw"] > r["options"]["on_grid"]["system_kw"]


def test_sunnier_city_needs_a_smaller_system():
    assert sizing.calculate_options([600], "quetta")["options"]["on_grid"]["system_kw"] < \
        sizing.calculate_options([600], "islamabad")["options"]["on_grid"]["system_kw"]


def test_roof_limits_the_number_of_panels():
    r = sizing.calculate_options([1500], "islamabad", roof_area_sqft=300)
    assert r["options"]["on_grid"]["panels"] == int(300 / 10.764 // 3.2)
    assert any("roof" in n.lower() for n in r["notes"])


def test_tiny_roof_is_refused():
    with pytest.raises(ValueError):
        sizing.calculate_options([300], "islamabad", roof_area_sqft=40)


def test_budget_is_flagged():
    r = sizing.calculate_options([500], "islamabad", outage_hours=4, budget_rs=600_000)
    assert r["options"]["hybrid"]["over_budget"] is True
    assert "budget" in r["reason"]


def test_twelve_months_of_bills_are_used_as_they_are():
    months = [300, 280, 350, 450, 600, 800, 850, 820, 650, 450, 320, 300]
    r = sizing.calculate_options(months, "multan")
    assert r["inputs"]["monthly_units"] == months
    assert r["options"]["on_grid"]["months"][6]["used"] == 850


def test_unknown_city_uses_the_pakistan_average():
    r = sizing.calculate_options([300], "Some Village")
    assert r["inputs"]["city"] == "other" and "Pakistan" in r["sunlight"]["source"]


def test_no_units_is_an_error():
    with pytest.raises(ValueError):
        sizing.calculate_options([], "islamabad")


def test_prices_change_the_quote():
    cheap = sizing.calculate_options([500], "islamabad", prices={"panel_price_per_watt": 30})
    normal = sizing.calculate_options([500], "islamabad")
    assert cheap["options"]["on_grid"]["cost"]["total"] < normal["options"]["on_grid"]["cost"]["total"]


def test_summary_is_small_and_has_every_option():
    s = sizing.summary(sizing.calculate_options([500], "islamabad"))
    assert set(("on_grid", "hybrid", "off_grid")) <= set(s)
    assert "months" not in s["on_grid"]


# ---------------------------------------------------------------------------
# Version 2: load-shedding schedules, WAPDA choices, NASA sunlight, packages, instalments
# ---------------------------------------------------------------------------
from app.services import sunlight  # noqa: E402


def test_weekly_daytime_load_shedding_is_understood():
    """'Light goes once a week from 9 am to 2 pm' - not 5 hours every day."""
    out = sizing.outage_profile(days_per_week=1, start_hour=9, end_hour=14)
    assert out["hours_per_cut"] == 5 and out["hours_per_week"] == 5
    assert out["daylight_hours"] == 5 and out["dark_hours"] == 0
    assert "9 am-2 pm" in out["text"]


def test_night_cut_that_passes_midnight():
    out = sizing.outage_profile(start_hour=22, end_hour=2)
    assert out["hours_per_cut"] == 4 and out["dark_hours"] == 4 and out["days_per_week"] == 7


def test_rare_daytime_cut_keeps_on_grid_but_warns():
    r = sizing.calculate_options([400], "islamabad", outage_days_per_week=1, outage_start_hour=10,
                                 outage_end_hour=12)
    assert r["recommended"] == "on_grid"
    assert "switches off" in r["reason"]


def test_daytime_cuts_need_a_smaller_battery_than_night_cuts():
    day = sizing.calculate_options([500], "lahore", outage_start_hour=9, outage_end_hour=14, backup_load_w=2000)
    night = sizing.calculate_options([500], "lahore", outage_start_hour=19, outage_end_hour=24, backup_load_w=2000)
    assert day["recommended"] == night["recommended"] == "hybrid"
    assert day["options"]["hybrid"]["battery_kwh"] < night["options"]["hybrid"]["battery_kwh"]
    assert night["options"]["hybrid"]["backup_hours"] >= 5


def test_on_grid_loses_sunshine_during_daytime_cuts():
    none = sizing.calculate_options([500], "lahore")["options"]["on_grid"]["yearly_generation"]
    cuts = sizing.calculate_options([500], "lahore", outage_start_hour=9, outage_end_hour=14)
    assert cuts["options"]["on_grid"]["yearly_generation"] < none
    assert cuts["options"]["hybrid"]["yearly_generation"] == pytest.approx(
        sizing.calculate_options([500], "lahore")["options"]["hybrid"]["yearly_generation"], rel=0.01)


def test_every_wapda_situation_has_a_bill():
    r = sizing.calculate_options([500], "islamabad")
    on = {s["key"]: s for s in r["options"]["on_grid"]["scenarios"]}
    off = {s["key"]: s for s in r["options"]["off_grid"]["scenarios"]}
    assert on["net_billing"]["monthly_bill"] < on["no_export"]["monthly_bill"] < r["current_bill"]["total"]
    assert off["disconnected"]["monthly_bill"] == 0
    assert 0 < off["wapda_backup"]["monthly_bill"] < r["current_bill"]["total"]


def test_customer_who_wants_no_green_meter():
    r = sizing.calculate_options([500], "islamabad", grid_choice="no_export")
    on = r["options"]["on_grid"]
    assert on["main_scenario"] == "no_export"
    assert on["monthly_bill_after"] == next(s["monthly_bill"] for s in on["scenarios"] if s["key"] == "no_export")


def test_customer_who_wants_to_leave_wapda():
    r = sizing.calculate_options([400], "rawalpindi", grid_choice="off_grid")
    assert r["recommended"] == "off_grid" and "independent" in r["reason"]
    off = r["options"]["off_grid"]
    assert off["system_kw"] > r["options"]["on_grid"]["system_kw"]       # sized for winter
    assert off["monthly_saving"] >= r["current_bill"]["total"] * 0.99     # no bill at all


def test_off_grid_warns_about_short_winter_months():
    r = sizing.calculate_options([300, 300, 300, 400, 600, 900, 900, 900, 700, 400, 300, 300], "lahore",
                                 grid_choice="off_grid", roof_area_sqft=300)
    assert r["options"]["off_grid"]["short_months"]
    assert any("Off-grid" in n for n in r["notes"])


def test_packages_and_instalments():
    r = sizing.calculate_options([500], "islamabad")
    totals = {p["tier"]: p["total"] for p in r["packages"]}
    assert totals["economy"] < totals["standard"] < totals["premium"]
    assert totals["standard"] == r["options"][r["recommended"]]["cost"]["total"]
    plans = r["financing"]["plans"]
    assert [p["months"] for p in plans] == [12, 24, 36]
    assert plans[0]["monthly"] > plans[2]["monthly"]
    assert sizing.instalment(120_000, 12, 0) == 10_000
    assert sizing.instalment(100_000, 12, 18) == 9168                     # standard loan formula


def test_nasa_values_give_a_realistic_yield():
    # NASA long-term daily sunlight for Islamabad (kWh/m2/day), Jan..Dec
    islamabad = [3.0, 3.9, 4.9, 6.0, 6.9, 7.1, 6.0, 5.6, 5.4, 4.6, 3.5, 2.8]
    monthly = sunlight.from_nasa_values(islamabad)
    assert 1400 <= sum(monthly) <= 1600            # PVGIS / real systems in Islamabad: ~1450-1550
    assert monthly[0] < monthly[4]                 # January makes less than May


def test_nasa_sunlight_is_used_when_given():
    solar = {"monthly_kwh_per_kw": [150] * 12, "yearly_kwh_per_kw": 1800, "source": "NASA POWER test", "nasa": True}
    r = sizing.calculate_options([600], "islamabad", solar=solar)
    assert r["sunlight"]["source"] == "NASA POWER test"
    assert r["options"]["on_grid"]["system_kw"] == pytest.approx(7200 / 1800, rel=0.15)


def test_browser_location_outside_pakistan_is_ignored():
    assert sunlight.location_for("lahore", 51.5, -0.1)[2] == "Lahore"
    assert sunlight.location_for(None, 33.6, 73.0)[2] == "your location"


def test_once_a_week_daytime_cut_stays_on_grid():
    """The customer's real case: light goes once a week, 9 am to 2 pm."""
    r = sizing.calculate_options([437], "rawalpindi", outage_days_per_week=1, outage_start_hour=9,
                                 outage_end_hour=14, backup_load_w=400)
    assert r["recommended"] == "on_grid"
    assert "9 am-2 pm" in r["reason"]
