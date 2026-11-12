"""Data layer: load bond data from CSV and validate it before any calculation.

Principle: reject bad data at the door, with a message that names the faulty
bond, instead of letting it produce a wrong curve later.
"""

from pathlib import Path

import pandas as pd

from yieldcurve.instruments import bond_cash_flows

REQUIRED_COLUMNS = ["bond_id", "maturity_years", "coupon_rate", "face_value", "price"]


def load_bonds(csv_path: str | Path) -> pd.DataFrame:
    """Load a bond CSV, validate it, and return it sorted by maturity.

    Expected columns: bond_id, maturity_years, coupon_rate (decimal),
    face_value, price (per face_value, same units).
    """
    bonds = pd.read_csv(csv_path)

    # 1. Structure: every required column is present.
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in bonds.columns]
    if missing_columns:
        raise ValueError(f"Missing columns: {missing_columns}")

    # 2. Completeness: no empty cells.
    if bonds[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError("Some cells are empty. Every bond needs all fields.")

    # 3. Identity: each bond appears once.
    duplicated_ids = bonds.loc[bonds["bond_id"].duplicated(), "bond_id"].tolist()
    if duplicated_ids:
        raise ValueError(f"Duplicated bond_id: {duplicated_ids}")

    # 4. Prices: a bond always costs something.
    for bond in bonds.itertuples():
        if bond.price <= 0:
            raise ValueError(f"Bond {bond.bond_id}: price={bond.price} must be positive.")

    # 5. Contract terms: reuse the rules of bond_cash_flows (single source of truth),
    #    and add the bond_id to the error message.
    for bond in bonds.itertuples():
        try:
            bond_cash_flows(bond.face_value, bond.coupon_rate, bond.maturity_years)
        except ValueError as error:
            raise ValueError(f"Bond {bond.bond_id}: {error}") from error

    # The bootstrap solves maturities from shortest to longest.
    return bonds.sort_values("maturity_years").reset_index(drop=True)
