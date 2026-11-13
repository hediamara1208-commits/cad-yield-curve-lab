"""Tests for the bootstrap.

Two independent checks:
1. Recovery: the bootstrap finds the reference curve that generated the prices.
2. Repricing: the bootstrapped curve gives back every market price.
"""

from pathlib import Path

import pandas as pd
import pytest

from yieldcurve.curve import (
    bootstrap_discount_factors,
    build_curve_table,
    forward_rate,
    one_year_forward_rates,
    zero_rates_from_discount_factors,
)
from yieldcurve.data import load_bonds
from yieldcurve.instruments import bond_cash_flows
from yieldcurve.pricing import price_from_discount_factors

DATA_DIR = Path(__file__).parent.parent / "data"

# Prices are rounded to 4 decimals (error <= 0.00005 on ~100), so recovered
# DFs can differ from the reference by about 1e-6. 1e-5 leaves a margin.
DF_TOLERANCE = 1e-5


def make_bonds(rows: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(
        rows, columns=["bond_id", "maturity_years", "coupon_rate", "face_value", "price"]
    )


def reference_discount_factors() -> dict[int, float]:
    curve = pd.read_csv(DATA_DIR / "reference_zero_curve.csv")
    return {
        int(row.maturity_years): 1 / (1 + row.zero_rate) ** row.maturity_years
        for row in curve.itertuples()
    }


def test_hand_example_bonds_a_and_b():
    # Worked example in LEARNING_NOTES.md.
    bonds = make_bonds([("A", 1, 0.0, 100, 97.0874), ("B", 2, 0.03, 100, 99.6241)])
    discount_factors = bootstrap_discount_factors(bonds)
    assert discount_factors[1] == pytest.approx(0.970874, abs=1e-6)
    assert discount_factors[2] == pytest.approx(0.938946, abs=1e-6)


def test_bootstrap_recovers_reference_curve():
    bonds = load_bonds(DATA_DIR / "synthetic_bonds.csv")
    bootstrapped = bootstrap_discount_factors(bonds)
    reference = reference_discount_factors()

    assert sorted(bootstrapped) == sorted(reference)
    for maturity in reference:
        assert bootstrapped[maturity] == pytest.approx(
            reference[maturity], abs=DF_TOLERANCE
        ), f"DF({maturity})"


def test_bootstrapped_curve_reprices_every_bond_exactly():
    bonds = load_bonds(DATA_DIR / "synthetic_bonds.csv")
    discount_factors = bootstrap_discount_factors(bonds)

    for bond in bonds.itertuples():
        cash_flows = bond_cash_flows(
            bond.face_value, bond.coupon_rate, bond.maturity_years
        )
        model_price = price_from_discount_factors(cash_flows, discount_factors)
        # Exact up to floating-point error: each DF was solved from this price.
        assert model_price == pytest.approx(bond.price, abs=1e-10), bond.bond_id


def test_gap_in_maturities_is_rejected():
    bonds = make_bonds([("A", 1, 0.0, 100, 97.0), ("C", 3, 0.035, 100, 100.0)])
    with pytest.raises(ValueError, match="Maturities"):
        bootstrap_discount_factors(bonds)


def test_unsorted_bonds_are_rejected():
    bonds = make_bonds([("B", 2, 0.03, 100, 99.6), ("A", 1, 0.0, 100, 97.0)])
    with pytest.raises(ValueError, match="Maturities"):
        bootstrap_discount_factors(bonds)


# Rates are decimals: 1 basis point = 0.0001, so 1e-5 = 0.1 bp.
RATE_TOLERANCE = 1e-5


def test_zero_rate_hand_example():
    zero_rates = zero_rates_from_discount_factors({1: 0.970874, 2: 0.938946})
    assert zero_rates[1] == pytest.approx(0.0300, abs=RATE_TOLERANCE)
    assert zero_rates[2] == pytest.approx(0.0320, abs=RATE_TOLERANCE)


def test_bootstrap_recovers_reference_zero_rates():
    bonds = load_bonds(DATA_DIR / "synthetic_bonds.csv")
    zero_rates = zero_rates_from_discount_factors(bootstrap_discount_factors(bonds))
    reference = pd.read_csv(DATA_DIR / "reference_zero_curve.csv")

    for row in reference.itertuples():
        assert zero_rates[row.maturity_years] == pytest.approx(
            row.zero_rate, abs=RATE_TOLERANCE
        ), f"z({row.maturity_years})"


def test_zero_rate_round_trip():
    # DF -> z -> DF must give back the original DF.
    discount_factors = {1: 0.97, 3: 0.90, 10: 0.70}
    zero_rates = zero_rates_from_discount_factors(discount_factors)
    for maturity, discount_factor in discount_factors.items():
        rebuilt = 1 / (1 + zero_rates[maturity]) ** maturity
        assert rebuilt == pytest.approx(discount_factor, abs=1e-12)


def test_zero_rate_rejects_non_positive_discount_factor():
    with pytest.raises(ValueError):
        zero_rates_from_discount_factors({1: 0.0})


def test_forward_hand_example():
    # f(1,2) = 0.970874 / 0.938946 - 1 = 3.40%
    assert forward_rate(1, 0.970874, 2, 0.938946) == pytest.approx(0.0340, abs=RATE_TOLERANCE)


def test_first_forward_equals_first_zero_rate():
    # f(0,1) starts today, so it is the 1-year zero rate.
    forwards = one_year_forward_rates({1: 0.970874, 2: 0.938946})
    assert forwards[(0, 1)] == pytest.approx(0.0300, abs=RATE_TOLERANCE)


def test_flat_curve_has_flat_forwards():
    flat_rate = 0.034
    discount_factors = {t: 1 / (1 + flat_rate) ** t for t in range(1, 6)}
    for rate in one_year_forward_rates(discount_factors).values():
        assert rate == pytest.approx(flat_rate, abs=1e-12)


def test_chaining_forwards_gives_back_the_zero_rate():
    # (1+f01)(1+f12)...(1+f45) = (1+z5)^5: same money, same horizon.
    bonds = load_bonds(DATA_DIR / "synthetic_bonds.csv")
    discount_factors = bootstrap_discount_factors(bonds)
    growth = 1.0
    for rate in one_year_forward_rates(discount_factors).values():
        growth *= 1 + rate
    zero_rate_5y = zero_rates_from_discount_factors(discount_factors)[5]
    assert growth == pytest.approx((1 + zero_rate_5y) ** 5, abs=1e-12)


def test_forward_rejects_end_before_start():
    with pytest.raises(ValueError):
        forward_rate(2, 0.94, 1, 0.97)


def test_curve_table_matches_individual_functions():
    bonds = load_bonds(DATA_DIR / "synthetic_bonds.csv")
    table = build_curve_table(bonds)

    assert table["maturity_years"].tolist() == [1, 2, 3, 4, 5]
    assert table["zero_rate"].tolist() == pytest.approx(
        [0.0300, 0.0320, 0.0340, 0.0355, 0.0365], abs=RATE_TOLERANCE
    )
    assert table["forward_rate"].tolist() == pytest.approx(
        [0.0300, 0.0340, 0.0380, 0.0400, 0.0405], abs=1e-4
    )


def test_inconsistent_price_is_rejected():
    # B at 2.00 is absurd: its first coupon alone is worth 3 * 0.97 = 2.91.
    bonds = make_bonds([("A", 1, 0.0, 100, 97.0), ("B", 2, 0.03, 100, 2.0)])
    with pytest.raises(ValueError, match="Bond B"):
        bootstrap_discount_factors(bonds)
