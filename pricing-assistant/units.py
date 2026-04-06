class UnitError(ValueError):
    pass

WEIGHT_TO_G = {
    "g": 1.0,
    "kg": 1000.0,
    "oz": 28.349523125,
    "lb": 453.59237,
}

VOLUME_TO_ML = {
    "ml": 1.0,
    "l": 1000.0,
    "floz": 29.5735295625,   # US fluid oz
    "gal": 3785.411784,      # US gallon
}

COUNT_UNITS = {"each", "count", "unit", "pc", "pcs"}

def normalize_unit(u: str) -> str:
    u = (u or "").strip().lower()
    u = u.replace("fl oz", "floz").replace("fl_oz", "floz").replace("fluid ounce", "floz")
    u = u.replace("pound", "lb").replace("pounds", "lb")
    u = u.replace("ounces", "oz").replace("ounce", "oz")
    u = u.replace("grams", "g").replace("gram", "g")
    u = u.replace("kilograms", "kg").replace("kilogram", "kg")
    u = u.replace("liters", "l").replace("liter", "l")
    u = u.replace("gallons", "gal").replace("gallon", "gal")
    return u

def unit_type(u: str) -> str:
    u = normalize_unit(u)
    if u in WEIGHT_TO_G:
        return "weight"
    if u in VOLUME_TO_ML:
        return "volume"
    if u in COUNT_UNITS:
        return "count"
    raise UnitError(f"Unsupported unit: '{u}'. Use lb/oz/g/kg, ml/l/floz/gal, or each.")

def convert(value: float, from_unit: str, to_unit: str) -> float:
    fu = normalize_unit(from_unit)
    tu = normalize_unit(to_unit)

    ft = unit_type(fu)
    tt = unit_type(tu)
    if ft != tt:
        raise UnitError(f"Unit mismatch: cannot convert {fu} ({ft}) to {tu} ({tt}).")

    if ft == "weight":
        g = value * WEIGHT_TO_G[fu]
        return g / WEIGHT_TO_G[tu]

    if ft == "volume":
        ml = value * VOLUME_TO_ML[fu]
        return ml / VOLUME_TO_ML[tu]

    return value  # count treated 1:1
