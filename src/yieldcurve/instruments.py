"""Instrument layer: fixed-coupon bonds and their cash flow schedules.

Conventions (see ASSUMPTIONS.md):
- Annual coupons, integer maturities in years.
- Rates are decimals (0.035 means 3.5%), never percentages.
- Valuation date is a coupon date, so accrued interest is zero.
"""

MAX_COUPON_RATE = 0.50  # 50% as a decimal


def bond_cash_flows(
    face_value: float, coupon_rate: float, maturity_years: int
) -> list[tuple[int, float]]:
    """Return the annual cash flows of a fixed-coupon bullet bond.

    Each element is (time_in_years, amount). The final element includes
    the repayment of the face value.

    Example:
        bond_cash_flows(100, 0.035, 3) -> [(1, 3.5), (2, 3.5), (3, 103.5)]
    """
    if face_value <= 0:
        raise ValueError(f"face_value={face_value} must be positive.")

    # Our model uses annual coupons, so maturities are whole years (see ASSUMPTIONS.md).
    if not isinstance(maturity_years, int) or maturity_years < 1:
        raise ValueError(
            f"maturity_years={maturity_years} must be a whole number of years >= 1."
        )

    # Catch rates entered in percent by mistake (e.g. 4 instead of 0.04).
    # 50% is a project choice (see ASSUMPTIONS.md), not a market limit.
    if coupon_rate < 0 or coupon_rate > MAX_COUPON_RATE:
        raise ValueError(
            f"coupon_rate={coupon_rate} is outside [0, {MAX_COUPON_RATE}]. "
            "Rates must be decimals: use 0.04 for 4%."
        )

    coupon_amount = face_value * coupon_rate

    cash_flows = []
    for year in range(1, maturity_years + 1):
        amount = coupon_amount
        if year == maturity_years:
            amount += face_value  # principal repaid at maturity
        cash_flows.append((year, amount))

    return cash_flows
