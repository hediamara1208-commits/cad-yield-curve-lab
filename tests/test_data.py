"""Tests for the data layer.

`tmp_path` is a pytest fixture: pytest gives each test a fresh empty folder,
so we can write small, deliberately broken CSV files without touching data/.
"""

from pathlib import Path

import numpy as np
import pytest

from yieldcurve.data import load_bonds
from yieldcurve.instruments import bond_cash_flows

DATA_DIR = Path(__file__).parent.parent / "data"
HEADER = "bond_id,maturity_years,coupon_rate,face_value,price\n"


def write_csv(folder: Path, rows: str) -> Path:
    path = folder / "bonds.csv"
    path.write_text(HEADER + rows)
    return path


def test_synthetic_dataset_loads():
    bonds = load_bonds(DATA_DIR / "synthetic_bonds.csv")
    assert bonds["bond_id"].tolist() == ["A", "B", "C", "D", "E"]


def test_bonds_are_sorted_by_maturity(tmp_path):
    path = write_csv(tmp_path, "LONG,3,0.03,100,99\nSHORT,1,0.0,100,97\n")
    bonds = load_bonds(path)
    assert bonds["bond_id"].tolist() == ["SHORT", "LONG"]


def test_missing_column_is_rejected(tmp_path):
    path = tmp_path / "bonds.csv"
    path.write_text("bond_id,maturity_years,coupon_rate,face_value\nA,1,0.0,100\n")
    with pytest.raises(ValueError, match="Missing columns"):
        load_bonds(path)


def test_empty_cell_is_rejected(tmp_path):
    path = write_csv(tmp_path, "A,1,0.0,100,\n")
    with pytest.raises(ValueError, match="empty"):
        load_bonds(path)


def test_duplicated_bond_id_is_rejected(tmp_path):
    path = write_csv(tmp_path, "A,1,0.0,100,97\nA,2,0.03,100,99\n")
    with pytest.raises(ValueError, match="Duplicated"):
        load_bonds(path)


def test_non_positive_price_is_rejected(tmp_path):
    path = write_csv(tmp_path, "A,1,0.0,100,-97\n")
    with pytest.raises(ValueError, match="price"):
        load_bonds(path)


def test_coupon_in_percent_is_rejected_with_bond_id(tmp_path):
    path = write_csv(tmp_path, "A,1,0.0,100,97\nB,2,3,100,99\n")
    with pytest.raises(ValueError, match="Bond B"):
        load_bonds(path)


def test_numpy_integer_maturity_is_accepted():
    # pandas returns numpy.int64 for integer columns.
    cash_flows = bond_cash_flows(100, 0.03, np.int64(2))
    assert [time for time, _ in cash_flows] == [1, 2]
