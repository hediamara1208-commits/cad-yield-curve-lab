"""Curve engine: build discount factors from bond prices (bootstrapping).

Method (educational, see ASSUMPTIONS.md):
- One bond per annual maturity 1, 2, ..., N, no gaps, so no interpolation.
- Bonds are processed from shortest to longest maturity.
- For a bond maturing at T, every DF before T is already known. Only DF(T)
  is unknown, so the pricing equation can be solved for it directly:

      price = (value of cash flows before T) + (final cash flow) * DF(T)

      DF(T) = (price - value of cash flows before T) / final cash flow
"""

import pandas as pd

from yieldcurve.instruments import bond_cash_flows
from yieldcurve.pricing import price_from_discount_factors


def bootstrap_discount_factors(bonds: pd.DataFrame) -> dict[int, float]:
    """Return {maturity_in_years: DF} solved sequentially from bond prices.

    `bonds` must come from load_bonds: validated and sorted by maturity.
    """
    check_maturities_are_consecutive_years(bonds)

    discount_factors: dict[int, float] = {}

    for bond in bonds.itertuples():
        cash_flows = bond_cash_flows(
            bond.face_value, bond.coupon_rate, bond.maturity_years
        )

        # Split the cash flows: all known ones, and the last one (unknown DF).
        earlier_cash_flows = cash_flows[:-1]
        maturity, final_cash_flow = cash_flows[-1]

        # Value of the earlier cash flows, using DFs already bootstrapped.
        known_value = price_from_discount_factors(earlier_cash_flows, discount_factors)

        # Solve price = known_value + final_cash_flow * DF(T) for DF(T).
        discount_factor = (bond.price - known_value) / final_cash_flow

        if discount_factor <= 0:
            raise ValueError(
                f"Bond {bond.bond_id}: DF({maturity}) = {discount_factor:.6f} "
                "is not positive. Its price is inconsistent with the shorter bonds."
            )

        discount_factors[maturity] = discount_factor

    return discount_factors


def zero_rates_from_discount_factors(
    discount_factors: dict[int, float],
) -> dict[int, float]:
    """Convert each DF(T) into an annually compounded zero rate z(T), as a decimal.

    From DF(T) = 1 / (1 + z(T))^T:

        z(T) = DF(T)^(-1/T) - 1

    Example: DF(2) = 0.938946 -> z(2) = 0.938946^(-1/2) - 1 = 0.0320 (3.20%).
    """
    zero_rates = {}
    for maturity, discount_factor in discount_factors.items():
        if maturity <= 0 or discount_factor <= 0:
            raise ValueError(
                f"Need maturity > 0 and DF > 0, got T={maturity}, DF={discount_factor}."
            )
        zero_rates[maturity] = discount_factor ** (-1 / maturity) - 1
    return zero_rates


def discount_factors_from_zero_rates(zero_rates: dict[int, float]) -> dict[int, float]:
    """Inverse of zero_rates_from_discount_factors: DF(T) = 1 / (1 + z(T))^T."""
    discount_factors = {}
    for maturity, zero_rate in zero_rates.items():
        if maturity <= 0 or zero_rate <= -1:
            raise ValueError(f"Need maturity > 0 and z > -100%, got T={maturity}, z={zero_rate}.")
        discount_factors[maturity] = 1 / (1 + zero_rate) ** maturity
    return discount_factors


def forward_rate(
    start_time: float, start_df: float, end_time: float, end_df: float
) -> float:
    """Annually compounded forward rate between start_time and end_time, as a decimal.

    Investing 1 until end_time must equal investing until start_time, then
    rolling over at the forward rate:  (1/end_df) = (1/start_df) * (1+f)^(end-start)

        f = (start_df / end_df)^(1 / (end_time - start_time)) - 1
    """
    if end_time <= start_time:
        raise ValueError(f"end_time={end_time} must be after start_time={start_time}.")
    if start_df <= 0 or end_df <= 0:
        raise ValueError("Discount factors must be positive.")
    return (start_df / end_df) ** (1 / (end_time - start_time)) - 1


def one_year_forward_rates(
    discount_factors: dict[int, float],
) -> dict[tuple[int, int], float]:
    """Return {(T-1, T): f(T-1, T)} for each maturity T, using DF(0) = 1.

    Example: DF(1)=0.970874, DF(2)=0.938946 -> f(1,2) = 0.970874/0.938946 - 1 = 3.40%.
    """
    all_discount_factors = {0: 1.0, **discount_factors}  # DF(0) = 1: 1 $ today is worth 1 $
    forwards = {}
    for maturity in sorted(discount_factors):
        start = maturity - 1
        forwards[(start, maturity)] = forward_rate(
            start, all_discount_factors[start], maturity, all_discount_factors[maturity]
        )
    return forwards


def build_curve_table(bonds: pd.DataFrame) -> pd.DataFrame:
    """Run the full curve construction and return one row per maturity.

    Columns: maturity_years, discount_factor, zero_rate, forward_start,
    forward_rate (rates as decimals). forward_rate is f(forward_start, maturity).
    This is the single entry point the dashboard uses: no finance in the UI.
    """
    discount_factors = bootstrap_discount_factors(bonds)
    zero_rates = zero_rates_from_discount_factors(discount_factors)
    forwards = one_year_forward_rates(discount_factors)

    rows = [
        {
            "maturity_years": maturity,
            "discount_factor": discount_factors[maturity],
            "zero_rate": zero_rates[maturity],
            "forward_start": maturity - 1,
            "forward_rate": forwards[(maturity - 1, maturity)],
        }
        for maturity in sorted(discount_factors)
    ]
    return pd.DataFrame(rows)


def check_maturities_are_consecutive_years(bonds: pd.DataFrame) -> None:
    """Require maturities exactly 1, 2, ..., N in this order.

    A gap (e.g. 1, 3) would leave two unknown DFs in one equation, which our
    simple method cannot solve without interpolation.
    """
    maturities = bonds["maturity_years"].tolist()
    expected = list(range(1, len(maturities) + 1))
    if maturities != expected:
        raise ValueError(
            f"Maturities must be {expected} in this order, got {maturities}. "
            "Use load_bonds to sort, and provide one bond per year with no gap."
        )
