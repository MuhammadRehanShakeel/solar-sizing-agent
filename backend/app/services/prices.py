"""
prices.py - The installer's price list.

Prices live in the database (Prices table) so an admin can change them on the Prices page.
DEFAULT_PRICES is used to fill an empty database and whenever the database is not reachable.
Market estimates for Rawalpindi / Islamabad, October 2026 (sources in docs/HOW_IT_WORKS.md).
"""
import logging

from app.database import execute_query

log = logging.getLogger("prices")

# key: (label, value, unit, group)
DEFAULT_PRICES = {
    "panel_watt": ("Panel size", 585, "W", "Panels"),
    "panel_price_per_watt": ("Panel price (N-type, Tier-1)", 40, "Rs/W", "Panels"),
    "panel_area_m2": ("Roof area per panel (incl. spacing)", 3.2, "m²", "Panels"),
    "ongrid_inverter_base": ("On-grid inverter: base price", 40000, "Rs", "Inverters"),
    "ongrid_inverter_per_kw": ("On-grid inverter: per kW", 16000, "Rs/kW", "Inverters"),
    "hybrid_inverter_base": ("Hybrid inverter: base price", 60000, "Rs", "Inverters"),
    "hybrid_inverter_per_kw": ("Hybrid inverter: per kW", 24000, "Rs/kW", "Inverters"),
    "battery_per_kwh": ("Lithium (LiFePO4) battery", 80000, "Rs/kWh", "Batteries"),
    "battery_pack_kwh": ("Battery pack size", 5, "kWh", "Batteries"),
    "structure_per_kw": ("Mounting structure", 12000, "Rs/kW", "Installation"),
    "installation_base": ("Wiring, protection & labour: base", 25000, "Rs", "Installation"),
    "installation_per_kw": ("Wiring, protection & labour: per kW", 9000, "Rs/kW", "Installation"),
    "net_billing_fee": ("Green meter + DISCO approval (approx.)", 50000, "Rs", "Installation"),
    "margin_percent": ("Installer margin", 10, "%", "Business"),
    "export_rate": ("Net-billing export rate", 11, "Rs/unit", "Grid"),
    "economy_percent": ("Economy package price vs Standard", 85, "%", "Packages"),
    "premium_percent": ("Premium package price vs Standard", 125, "%", "Packages"),
    "finance_rate": ("Instalment plan markup (yearly)", 18, "%", "Financing"),
    "down_payment_percent": ("Instalment plan down payment", 25, "%", "Financing"),
}


def defaults() -> dict:
    return {key: value for key, (_, value, _, _) in DEFAULT_PRICES.items()}


def get_prices() -> dict:
    """Current prices as {key: number}. Falls back to the defaults if the database has a problem."""
    prices = defaults()
    try:
        for row in execute_query("SELECT price_key, value FROM Prices", fetch_all=True) or []:
            if row["price_key"] in prices:
                prices[row["price_key"]] = float(row["value"])
    except Exception:
        log.warning("Prices table not reachable - using default prices")
    return prices


def price_rows() -> list:
    """For the admin page and the agent's get_price_list tool: label, value, unit, group."""
    current = get_prices()
    return [{"key": key, "label": label, "value": current[key], "unit": unit, "group": group}
            for key, (label, _, unit, group) in DEFAULT_PRICES.items()]
