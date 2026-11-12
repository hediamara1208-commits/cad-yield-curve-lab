"""Pricing layer: value cash flows with a discount curve.

Core formula (any compounding convention, since DFs are already computed):

    price = sum over t of CF(t) * DF(t)

The price returned is a dirty price. Under our assumptions (valuation on a
coupon date, see ASSUMPTIONS.md), dirty price = clean price.
"""


def price_from_discount_factors(
    cash_flows: list[tuple[int, float]], discount_factors: dict[int, float]
) -> float:
    """Return the present value of cash flows, discounting each one with DF(t).

    Args:
        cash_flows: (time_in_years, amount) pairs, e.g. from bond_cash_flows.
        discount_factors: maps time_in_years to DF(t), e.g. {1: 0.970874, 2: 0.938946}.

    Example:
        price_from_discount_factors([(1, 3.0), (2, 103.0)], {1: 0.970874, 2: 0.938946})
        -> 3 * 0.970874 + 103 * 0.938946 = 99.6241
    """
    price = 0.0
    for time, amount in cash_flows:
        if time not in discount_factors:
            raise ValueError(
                f"No discount factor for t={time}. "
                f"Available times: {sorted(discount_factors)}."
            )
        price += amount * discount_factors[time]

    return price
