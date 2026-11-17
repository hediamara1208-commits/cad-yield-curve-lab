"""Tests for observed market analysis (offline, saved Valet sample)."""

import json
from pathlib import Path

import pandas as pd
import pytest

from yieldcurve.boc import parse_valet_observations
from yieldcurve.market import (
    available_date_on_or_before,
    compare_curves,
    curve_on_date,
    slope_bp,
)

SAMPLE = Path(__file__).parent / "fixtures" / "valet_sample.json"


def sample_table():
    return parse_valet_observations(json.loads(SAMPLE.read_text()))


def test_weekend_falls_back_to_last_business_day():
    # 2026-11-14 is a Saturday: use Friday 2026-11-13.
    assert available_date_on_or_before(sample_table(), "2026-11-14") == pd.Timestamp("2026-11-13")


def test_date_before_first_observation_is_rejected():
    with pytest.raises(ValueError, match="No data"):
        available_date_on_or_before(sample_table(), "2020-01-01")


def test_curve_on_date_values():
    used, curve = curve_on_date(sample_table(), "2026-11-12")
    assert used == pd.Timestamp("2026-11-12")
    assert curve[2] == pytest.approx(0.0333)
    assert curve[10] == pytest.approx(0.0378)


def test_compare_curves_change_in_bp():
    comparison = compare_curves(sample_table(), "2026-11-12", "2026-11-13")
    two_year = comparison[comparison["tenor_years"] == 2].iloc[0]
    assert two_year["change_bp"] == pytest.approx(4.0)  # 3.33% -> 3.37%


def test_compare_curves_keeps_only_tenors_on_both_dates():
    # The 7-year value is missing on 2026-11-13 in the sample.
    comparison = compare_curves(sample_table(), "2026-11-12", "2026-11-13")
    assert comparison["tenor_years"].tolist() == [2, 3, 5, 10]


def test_slope_2s10s_in_bp():
    slope = slope_bp(sample_table())
    assert slope.loc["2026-11-12"] == pytest.approx(45.0)  # 3.78% - 3.33%
    assert slope.loc["2026-11-13"] == pytest.approx(48.0)  # 3.85% - 3.37%
