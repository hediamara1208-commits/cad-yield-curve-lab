"""Tests for the Bank of Canada data layer. No network: a saved sample is used.

The sample copies the real Valet format (values from 12-13 Nov 2026), with the
7-year value on 13 Nov blanked on purpose to test missing data.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from yieldcurve.boc import (
    load_benchmark_yields,
    parse_valet_observations,
    save_benchmark_yields,
)

SAMPLE = Path(__file__).parent / "fixtures" / "valet_sample.json"


def sample_table() -> pd.DataFrame:
    return parse_valet_observations(json.loads(SAMPLE.read_text()))


def test_percent_is_converted_to_decimal():
    table = sample_table()
    two_year = table[(table["date"] == "2026-11-12") & (table["tenor_years"] == 2)]
    assert two_year["yield_rate"].iloc[0] == pytest.approx(0.0333)


def test_only_nominal_benchmarks_are_kept():
    # Long-term and Real Return Bond series are excluded.
    assert set(sample_table()["tenor_years"]) == {2, 3, 5, 7, 10}


def test_missing_value_is_skipped_not_guessed():
    table = sample_table()
    nov_13 = table[table["date"] == "2026-11-13"]
    assert nov_13["tenor_years"].tolist() == [2, 3, 5, 10]


def test_save_then_load_round_trip(tmp_path):
    path = tmp_path / "yields.csv"
    save_benchmark_yields(sample_table(), path)
    loaded = load_benchmark_yields(path)
    assert len(loaded) == 9
    assert loaded["yield_rate"].max() == pytest.approx(0.0385)


def test_percent_left_in_file_is_rejected(tmp_path):
    path = tmp_path / "yields.csv"
    path.write_text("date,tenor_years,yield_rate\n2026-11-13,2,3.37\n")
    with pytest.raises(ValueError, match="percent"):
        load_benchmark_yields(path)


def test_unexpected_tenor_is_rejected(tmp_path):
    path = tmp_path / "yields.csv"
    path.write_text("date,tenor_years,yield_rate\n2026-11-13,30,0.04\n")
    with pytest.raises(ValueError, match="tenors"):
        load_benchmark_yields(path)
