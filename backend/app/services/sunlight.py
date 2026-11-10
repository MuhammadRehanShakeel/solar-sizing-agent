"""
sunlight.py - How much electricity 1 kW of panels makes in each month, at the customer's location.

Source: NASA POWER (https://power.larc.nasa.gov), free, no key. It gives the long-term average
sunlight that reaches the ground (ALLSKY_SFC_SW_DWN, kWh per m2 per day) for any latitude/longitude,
measured by satellites over 20+ years.

    kWh per kW of panels in a month = sunlight per day x days x TILT_GAIN[month] x PERFORMANCE_RATIO

  TILT_GAIN          panels are tilted towards the south (~25-30 deg), so they catch more sun than a
                     flat surface, most of all in winter when the sun is low.
  PERFORMANCE_RATIO  real systems lose ~22 %: heat, dust, wiring, inverter. 0.78 is a normal value
                     for clean, well-installed systems in Pakistan.

If NASA cannot be reached (no internet), we fall back to a city table, so the app still works.
Answers are cached in memory and in data/sunlight_cache.json (NASA data does not change).
"""
import json
import logging
import os
import threading

from app import config

log = logging.getLogger("sunlight")
NASA_URL = ("https://power.larc.nasa.gov/api/temporal/climatology/point"
            "?parameters=ALLSKY_SFC_SW_DWN&community=RE&longitude={lon:.2f}&latitude={lat:.2f}&format=JSON")
MONTH_KEYS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAYS = [31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
TILT_GAIN = [1.28, 1.19, 1.08, 0.99, 0.94, 0.92, 0.93, 0.97, 1.04, 1.15, 1.26, 1.31]
PERFORMANCE_RATIO = 0.78

# City -> (latitude, longitude, kWh per kW per year used when NASA is not reachable)
CITIES = {
    "islamabad": (33.68, 73.05, 1450), "rawalpindi": (33.60, 73.04, 1450), "lahore": (31.55, 74.34, 1450),
    "karachi": (24.86, 67.01, 1600), "faisalabad": (31.42, 73.08, 1500), "multan": (30.20, 71.47, 1550),
    "peshawar": (34.01, 71.58, 1500), "quetta": (30.18, 66.98, 1750), "gujranwala": (32.16, 74.19, 1450),
    "sialkot": (32.49, 74.53, 1420), "hyderabad": (25.40, 68.37, 1600), "sukkur": (27.70, 68.86, 1580),
    "bahawalpur": (29.40, 71.68, 1580), "sargodha": (32.08, 72.67, 1500), "abbottabad": (34.15, 73.22, 1400),
    "mardan": (34.20, 72.04, 1480), "gujrat": (32.57, 74.08, 1450), "jhelum": (32.94, 73.73, 1460),
    "sheikhupura": (31.71, 73.99, 1450), "rahim yar khan": (28.42, 70.30, 1580), "sahiwal": (30.66, 73.11, 1500),
    "dera ghazi khan": (30.05, 70.63, 1580), "mirpur": (33.15, 73.75, 1450), "muzaffarabad": (34.37, 73.47, 1380),
    "gilgit": (35.92, 74.31, 1650), "taxila": (33.75, 72.80, 1450), "wah cantt": (33.78, 72.72, 1450),
    "attock": (33.77, 72.36, 1460), "chakwal": (32.93, 72.86, 1470), "murree": (33.91, 73.39, 1380),
}
# Month shape used only with the fallback table (winter fog, summer sun). Average = 1.0
SEASON = [0.72, 0.85, 1.00, 1.12, 1.20, 1.18, 1.05, 1.03, 1.05, 1.00, 0.86, 0.74]

_cache = {}
_lock = threading.Lock()
CACHE_FILE = os.path.join(config.DATA_DIR, "sunlight_cache.json")


def city_key(city: str) -> str:
    key = " ".join((city or "").strip().lower().split())
    return key if key in CITIES else "other"


def location_for(city: str = None, lat: float = None, lon: float = None):
    """(lat, lon, name). A browser location wins over the city name. Only Pakistan-ish boxes are accepted."""
    if lat is not None and lon is not None and 23 <= float(lat) <= 38 and 60 <= float(lon) <= 78:
        return round(float(lat), 2), round(float(lon), 2), "your location"
    key = city_key(city)
    if key == "other":
        return None, None, "Pakistan average"
    lat_, lon_, _ = CITIES[key]
    return lat_, lon_, key.title()


def _fallback(city: str) -> dict:
    key = city_key(city)
    yearly = CITIES[key][2] if key in CITIES else 1500
    monthly = [yearly / 365 * days * s for days, s in zip(DAYS, SEASON)]
    total = sum(monthly)
    monthly = [m * yearly / total for m in monthly]                 # make the 12 months add up exactly
    return {"monthly_kwh_per_kw": [round(m, 1) for m in monthly], "yearly_kwh_per_kw": round(sum(monthly)),
            "source": f"Average table for {key.title() if key in CITIES else 'Pakistan'} (NASA not reachable)",
            "nasa": False}


def from_nasa_values(daily_sunlight: list) -> list:
    """12 NASA monthly values (kWh/m2/day) -> kWh per kW of panels per month."""
    return [round(g * d * t * PERFORMANCE_RATIO, 1) for g, d, t in zip(daily_sunlight, DAYS, TILT_GAIN)]


def _load_cache():
    if _cache or not os.path.isfile(CACHE_FILE):
        return
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            _cache.update(json.load(f))
    except Exception:
        log.warning("Sunlight cache unreadable - ignoring it")


def _save_cache():
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f)
    except Exception:
        log.warning("Could not save the sunlight cache")


def _fetch_nasa(lat: float, lon: float) -> list:
    import httpx
    response = httpx.get(NASA_URL.format(lat=lat, lon=lon), timeout=config.NASA_TIMEOUT_SECONDS)
    response.raise_for_status()
    values = response.json()["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
    daily = [float(values[k]) for k in MONTH_KEYS]
    if not all(1.0 <= v <= 9.0 for v in daily):                      # sanity check: NASA uses -999 for "no data"
        raise ValueError(f"Unexpected NASA values: {daily}")
    return daily


def solar_yield(city: str = None, lat: float = None, lon: float = None) -> dict:
    """Monthly and yearly kWh per kW of panels + where the numbers come from."""
    lat_, lon_, place = location_for(city, lat, lon)
    if lat_ is None or not config.USE_NASA_SUNLIGHT:
        return _fallback(city)
    key = f"{lat_:.2f},{lon_:.2f}"
    with _lock:
        _load_cache()
        daily = _cache.get(key)
    if daily is None:
        try:
            daily = _fetch_nasa(lat_, lon_)
        except Exception as e:
            log.warning("NASA POWER not reachable for %s (%s) - using the city table", key, str(e)[:80])
            return _fallback(city)
        with _lock:
            _cache[key] = daily
            _save_cache()
    monthly = from_nasa_values(daily)
    return {"monthly_kwh_per_kw": monthly, "yearly_kwh_per_kw": round(sum(monthly)),
            "daily_sunlight_kwh_m2": daily, "lat": lat_, "lon": lon_,
            "source": f"NASA POWER satellite data, {place} ({lat_:.2f}, {lon_:.2f})", "nasa": True}
