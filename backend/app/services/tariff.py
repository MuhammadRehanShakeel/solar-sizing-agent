"""
tariff.py - Estimates a Pakistani domestic electricity bill (all DISCOs: IESCO, LESCO, ...).

Source: NEPRA domestic schedule S.R.O. 279(I)/2026 (February 2026). Rates change often:
update the tables below when NEPRA notifies a new schedule. FPA / QTA (monthly fuel
adjustments) and income tax are NOT included, so real bills can be a bit higher.

Two kinds of customer:
  * protected     : used <= 200 units every month for 6 months -> cheaper, progressive slabs
  * non-protected : everyone else -> the rate of the slab you land in applies to EVERY unit
"""

# (upper limit of the slab in units, Rs per unit)
NON_PROTECTED = [(100, 22.44), (200, 28.91), (300, 33.10), (400, 36.46), (500, 38.95),
                 (600, 40.22), (700, 41.85), (float("inf"), 47.20)]
PROTECTED = [(100, 10.54), (200, 13.01)]

# fixed charge per kW of sanctioned load per month: (upper limit in units, Rs per kW)
FIXED_NON_PROTECTED = [(100, 275), (200, 300), (300, 350), (400, 400), (500, 500), (float("inf"), 675)]
FIXED_PROTECTED = [(100, 200), (200, 300)]

FC_SURCHARGE = {"protected": 1.43, "non_protected": 3.23}     # Rs per unit
ELECTRICITY_DUTY = 0.015                                       # 1.5 % (Punjab)
GST = 0.18
PTV_FEE = 35

# Net billing (new solar users since 9 Feb 2026): exported units are bought at about the national
# average energy purchase price. The exact rupee rate is set by NEPRA; Rs 11 is the common estimate.
DEFAULT_EXPORT_RATE = 11.0


def _slab(table, units):
    for limit, value in table:
        if units <= limit:
            return value
    return table[-1][1]


def energy_charge(units: float, protected: bool = False) -> float:
    units = max(0.0, units)
    if protected and units <= 200:
        first = min(units, 100)
        return first * PROTECTED[0][1] + max(0.0, units - 100) * PROTECTED[1][1]
    return units * _slab(NON_PROTECTED, units)


def monthly_bill(units: float, sanctioned_load_kw: float = 5, protected: bool = False) -> dict:
    """Bill estimate for one month. Returns every part so the user can see where the money goes."""
    units = max(0.0, float(units))
    protected = protected and units <= 200
    energy = energy_charge(units, protected)
    fixed = _slab(FIXED_PROTECTED if protected else FIXED_NON_PROTECTED, units) * max(1.0, sanctioned_load_kw)
    fc = units * FC_SURCHARGE["protected" if protected else "non_protected"]
    duty = energy * ELECTRICITY_DUTY
    gst = (energy + fixed + fc + duty) * GST
    total = energy + fixed + fc + duty + gst + PTV_FEE
    return {"units": round(units), "energy": round(energy), "fixed": round(fixed), "fc_surcharge": round(fc),
            "electricity_duty": round(duty), "gst": round(gst), "ptv": PTV_FEE, "total": round(total),
            "rate_per_unit": round(_slab(NON_PROTECTED, units), 2) if not protected else None,
            "protected": protected}


def bill_with_solar(import_units: float, export_units: float, sanctioned_load_kw: float = 5,
                    export_rate: float = DEFAULT_EXPORT_RATE) -> dict:
    """Net billing: pay for what you take from the grid, get a credit for what you send to it."""
    bill = monthly_bill(import_units, sanctioned_load_kw, protected=False)
    credit = export_units * export_rate
    payable = bill["total"] - credit
    return {"import_units": round(import_units), "export_units": round(export_units),
            "bill_before_credit": bill["total"], "export_credit": round(credit),
            "payable": round(max(payable, bill["fixed"] + PTV_FEE))}     # fixed charges are always paid


def units_from_bill_amount(amount_rs: float, sanctioned_load_kw: float = 5) -> int:
    """'My bill is Rs 25,000' -> about how many units? (search over units, bills only go up with units)"""
    low, high = 0, 5000
    while low < high:
        mid = (low + high) // 2
        if monthly_bill(mid, sanctioned_load_kw)["total"] < amount_rs:
            low = mid + 1
        else:
            high = mid
    return low
