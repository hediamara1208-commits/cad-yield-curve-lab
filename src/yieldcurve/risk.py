"""Risk layer: interest rate scenarios on the zero curve.

Why shift the zero curve (and not each bond's yield)?
The zero curve gives ONE discount factor per date, shared by every bond.
Shifting it keeps the shocked market consistent: 1 $ at year 3 has a single
value, whichever bond pays it. Shifting each bond's yield would give the same
dollar different values depending on the bond.

Units: shifts are given in basis points (1 bp = 0.0001 in decimal).
"""

import pandas as pd

from yieldcurve.curve import (
    discount_factors_from_zero_rates,
    zero_rates_from_discount_factors,
)
from yieldcurve.instruments import bond_cash_flows
from yieldcurve.pricing import price_from_discount_factors

BASIS_POINT = 0.0001  # 1 bp as a decimal rate
STANDARD_SHIFTS_BP = [-100, -50, -25, 25, 50, 100]


def parallel_shift(discount_factors: dict[int, float], shift_bp: float) -> dict[int, float]:
    """Return the discount factors after adding shift_bp to every zero rate.

    Steps: DF -> zero rates (annual compounding) -> z + shift -> DF.
    Example: shift_bp=25 moves z(3) from 3.40% to 3.65%.
    """
    zero_rates = zero_rates_from_discount_factors(discount_factors)
    shifted_zero_rates = {
        maturity: rate + shift_bp * BASIS_POINT for maturity, rate in zero_rates.items()
    }
    return discount_factors_from_zero_rates(shifted_zero_rates)


def price_after_shift(
    cash_flows: list[tuple[int, float]], discount_factors: dict[int, float], shift_bp: float
) -> float:
    """Price of the cash flows on the curve shifted in parallel by shift_bp."""
    return price_from_discount_factors(cash_flows, parallel_shift(discount_factors, shift_bp))


def dv01(cash_flows: list[tuple[int, float]], discount_factors: dict[int, float]) -> float:
    """Price loss for a +1 bp parallel shift of the zero curve (finite difference).

    DV01 = P(base curve) - P(curve + 1 bp). Positive for a normal bond:
    rates up -> price down. Same units as the price (per 100 face here).
    """
    base_price = price_from_discount_factors(cash_flows, discount_factors)
    return base_price - price_after_shift(cash_flows, discount_factors, 1)


def scenario_table(
    bonds: pd.DataFrame,
    discount_factors: dict[int, float],
    shifts_bp: list[float] = STANDARD_SHIFTS_BP,
) -> pd.DataFrame:
    """One row per bond: base price, DV01, and price change under each shift.

    Columns: bond_id, maturity_years, base_price, dv01, then one
    'change_<shift>bp' column per shift (new price - base price).
    """
    rows = []
    for bond in bonds.itertuples():
        cash_flows = bond_cash_flows(bond.face_value, bond.coupon_rate, bond.maturity_years)
        base_price = price_from_discount_factors(cash_flows, discount_factors)
        row = {
            "bond_id": bond.bond_id,
            "maturity_years": bond.maturity_years,
            "base_price": base_price,
            "dv01": dv01(cash_flows, discount_factors),
        }
        for shift in shifts_bp:
            new_price = price_after_shift(cash_flows, discount_factors, shift)
            row[f"change_{shift:+g}bp"] = new_price - base_price
        rows.append(row)
    return pd.DataFrame(rows)
