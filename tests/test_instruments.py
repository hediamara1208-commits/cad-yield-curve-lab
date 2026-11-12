"""Tests for the instrument layer.

These tests are the specification of bond_cash_flows: they describe what
the function must return.

Times are integers, so they are compared exactly. Amounts are floats, so
they are compared with pytest.approx (e.g. 100 * 0.035 = 3.5000000000000004).
"""

import pytest

from yieldcurve.instruments import bond_cash_flows


def test_coupon_bond_three_years():
    cash_flows = bond_cash_flows(100, 0.035, 3)
    times = [time for time, _ in cash_flows]
    amounts = [amount for _, amount in cash_flows]

    assert times == [1, 2, 3]
    assert amounts == pytest.approx([3.5, 3.5, 103.5])


def test_zero_coupon_bond_one_year():
    cash_flows = bond_cash_flows(100, 0.0, 1)
    times = [time for time, _ in cash_flows]
    amounts = [amount for _, amount in cash_flows]

    assert times == [1]
    assert amounts == pytest.approx([100.0])


def test_coupon_given_in_percent_is_rejected():
    with pytest.raises(ValueError):
        bond_cash_flows(100, 4, 5)  # meant 4%, wrote 4 (= 400%)


def test_negative_coupon_is_rejected():
    with pytest.raises(ValueError):
        bond_cash_flows(100, -0.01, 3)


def test_high_but_realistic_coupon_is_accepted():
    # Canadian coupons above 10% existed in the early 1980s.
    cash_flows = bond_cash_flows(100, 0.12, 2)
    amounts = [amount for _, amount in cash_flows]
    assert amounts == pytest.approx([12.0, 112.0])


@pytest.mark.parametrize("bad_maturity", [0, -3, 2.5])
def test_invalid_maturity_is_rejected(bad_maturity):
    with pytest.raises(ValueError):
        bond_cash_flows(100, 0.03, bad_maturity)


@pytest.mark.parametrize("bad_face_value", [0, -100])
def test_invalid_face_value_is_rejected(bad_face_value):
    with pytest.raises(ValueError):
        bond_cash_flows(bad_face_value, 0.03, 2)


def test_coupon_at_the_threshold_is_accepted():
    cash_flows = bond_cash_flows(100, 0.50, 1)
    amounts = [amount for _, amount in cash_flows]
    assert amounts == pytest.approx([150.0])
