"""Tests for interest rate scenarios."""

import pytest

from yieldcurve.curve import discount_factors_from_zero_rates, zero_rates_from_discount_factors
from yieldcurve.instruments import bond_cash_flows
from yieldcurve.pricing import price_from_discount_factors
from yieldcurve.risk import dv01, parallel_shift, price_after_shift, scenario_table

REFERENCE_ZERO_RATES = {1: 0.0300, 2: 0.0320, 3: 0.0340, 4: 0.0355, 5: 0.0365}


def reference_discount_factors() -> dict[int, float]:
    return discount_factors_from_zero_rates(REFERENCE_ZERO_RATES)


def test_zero_to_discount_factor_round_trip():
    zero_rates = zero_rates_from_discount_factors(reference_discount_factors())
    for maturity, rate in REFERENCE_ZERO_RATES.items():
        assert zero_rates[maturity] == pytest.approx(rate, abs=1e-12)


def test_zero_shift_changes_nothing():
    original = reference_discount_factors()
    shifted = parallel_shift(original, 0)
    for maturity in original:
        assert shifted[maturity] == pytest.approx(original[maturity], abs=1e-12)


@pytest.mark.parametrize("shift_bp", [-100, -25, 1, 25, 100])
def test_every_zero_rate_moves_by_the_shift(shift_bp):
    shifted_zero_rates = zero_rates_from_discount_factors(
        parallel_shift(reference_discount_factors(), shift_bp)
    )
    for maturity, rate in REFERENCE_ZERO_RATES.items():
        assert shifted_zero_rates[maturity] == pytest.approx(rate + shift_bp * 0.0001, abs=1e-12)


def test_hand_example_plus_25bp_at_3_years():
    # z(3): 3.40% -> 3.65%, so DF(3) = 1 / 1.0365^3
    shifted = parallel_shift(reference_discount_factors(), 25)
    assert shifted[3] == pytest.approx(1 / 1.0365**3, abs=1e-12)


BOND_C = bond_cash_flows(100, 0.035, 3)


def test_zero_shift_keeps_the_price():
    discount_factors = reference_discount_factors()
    base = price_from_discount_factors(BOND_C, discount_factors)
    assert price_after_shift(BOND_C, discount_factors, 0) == pytest.approx(base, abs=1e-12)


def test_rates_up_price_down_rates_down_price_up():
    discount_factors = reference_discount_factors()
    base = price_from_discount_factors(BOND_C, discount_factors)
    assert price_after_shift(BOND_C, discount_factors, 25) < base
    assert price_after_shift(BOND_C, discount_factors, -25) > base


def test_dv01_of_zero_coupon_by_hand():
    # 100 at 1 year: DV01 = 100 / 1.03 - 100 / 1.0301
    discount_factors = reference_discount_factors()
    expected = 100 / 1.03 - 100 / 1.0301
    assert dv01([(1, 100.0)], discount_factors) == pytest.approx(expected, abs=1e-12)


def test_dv01_of_bond_c_matches_derivative_estimate():
    # Derivative estimate: sum of T * CF * DF / (1 + z) * 0.0001 = 0.0281 (see LEARNING_NOTES).
    assert dv01(BOND_C, reference_discount_factors()) == pytest.approx(0.0281, abs=1e-4)


def test_longer_bond_has_larger_dv01():
    discount_factors = reference_discount_factors()
    bond_a = bond_cash_flows(100, 0.0, 1)
    bond_e = bond_cash_flows(100, 0.04, 5)
    assert dv01(bond_e, discount_factors) > dv01(bond_a, discount_factors)


def test_convexity_dv01_overstates_loss_and_understates_gain():
    # Price vs rate is convex: for +100 bp the loss is smaller than 100 x DV01,
    # for -100 bp the gain is larger than 100 x DV01.
    discount_factors = reference_discount_factors()
    base = price_from_discount_factors(BOND_C, discount_factors)
    linear_estimate = 100 * dv01(BOND_C, discount_factors)
    loss_up = base - price_after_shift(BOND_C, discount_factors, 100)
    gain_down = price_after_shift(BOND_C, discount_factors, -100) - base
    assert loss_up < linear_estimate < gain_down


def test_scenario_table_columns_and_signs():
    import pandas as pd

    bonds = pd.DataFrame(
        [("C", 3, 0.035, 100, 100.3065)],
        columns=["bond_id", "maturity_years", "coupon_rate", "face_value", "price"],
    )
    table = scenario_table(bonds, reference_discount_factors(), [-25, 25])
    assert list(table.columns) == [
        "bond_id", "maturity_years", "base_price", "dv01", "change_-25bp", "change_+25bp",
    ]
    assert table.loc[0, "change_+25bp"] < 0 < table.loc[0, "change_-25bp"]


def test_rates_up_means_discount_factors_down():
    original = reference_discount_factors()
    up = parallel_shift(original, 25)
    down = parallel_shift(original, -25)
    for maturity in original:
        assert up[maturity] < original[maturity] < down[maturity]
