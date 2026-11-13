"""Tests for the pricing layer."""

from pathlib import Path

import pandas as pd
import pytest

from yieldcurve.instruments import bond_cash_flows
from yieldcurve.pricing import cash_flow_breakdown, price_from_discount_factors

DATA_DIR = Path(__file__).parent.parent / "data"

# Dataset prices are rounded to 4 decimals, so they can differ from the
# exact model price by at most 0.00005.
PRICE_TOLERANCE = 1e-4


def reference_discount_factors() -> dict[int, float]:
    """DF(T) = 1 / (1 + z(T))^T from the reference zero curve (annual compounding)."""
    curve = pd.read_csv(DATA_DIR / "reference_zero_curve.csv")
    return {
        int(row.maturity_years): 1 / (1 + row.zero_rate) ** row.maturity_years
        for row in curve.itertuples()
    }


def test_zero_coupon_price_is_face_value_times_discount_factor():
    price = price_from_discount_factors([(1, 100.0)], {1: 0.97})
    assert price == pytest.approx(97.0)


def test_bond_b_by_hand():
    # 3 * 0.970874 + 103 * 0.938946 = 99.6241 (worked example in LEARNING_NOTES.md)
    price = price_from_discount_factors(
        [(1, 3.0), (2, 103.0)], {1: 0.970874, 2: 0.938946}
    )
    assert price == pytest.approx(99.6241, abs=PRICE_TOLERANCE)


def test_reference_curve_reprices_every_synthetic_bond():
    discount_factors = reference_discount_factors()
    bonds = pd.read_csv(DATA_DIR / "synthetic_bonds.csv")

    for bond in bonds.itertuples():
        cash_flows = bond_cash_flows(
            bond.face_value, bond.coupon_rate, bond.maturity_years
        )
        model_price = price_from_discount_factors(cash_flows, discount_factors)
        assert model_price == pytest.approx(bond.price, abs=PRICE_TOLERANCE), bond.bond_id


def test_breakdown_of_bond_b():
    rows = cash_flow_breakdown([(1, 3.0), (2, 103.0)], {1: 0.970874, 2: 0.938946})
    assert [row["time"] for row in rows] == [1, 2]
    assert rows[0]["present_value"] == pytest.approx(3 * 0.970874)
    assert rows[1]["present_value"] == pytest.approx(103 * 0.938946)


def test_breakdown_sums_to_price():
    discount_factors = reference_discount_factors()
    cash_flows = bond_cash_flows(100, 0.04, 5)
    rows = cash_flow_breakdown(cash_flows, discount_factors)
    total = sum(row["present_value"] for row in rows)
    assert total == pytest.approx(price_from_discount_factors(cash_flows, discount_factors))


def test_missing_discount_factor_is_rejected():
    with pytest.raises(ValueError):
        price_from_discount_factors([(1, 3.0), (2, 103.0)], {1: 0.97})
