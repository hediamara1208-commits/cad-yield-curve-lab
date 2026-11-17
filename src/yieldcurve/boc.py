"""Bank of Canada data layer: Government of Canada benchmark bond yields.

Source: Bank of Canada Valet API, group "bond_yields_benchmark"
(https://www.bankofcanada.ca/valet/). Business-daily observations.

What these numbers ARE:
- Yields to maturity of specific Government of Canada benchmark bonds
  (coupon bonds), as published by the Bank of Canada, in percent.

What they are NOT:
- Not zero-coupon rates. A yield to maturity summarises a coupon bond's
  price as one rate (like bond C's 3.39%), so these yields cannot be used
  as discount rates for single cash flows.
- Not bootstrappable as such: bootstrapping needs each bond's price,
  coupon and exact maturity, which this series does not provide.

Kept: the nominal 2, 3, 5, 7 and 10-year benchmarks.
Excluded: the long-term benchmark (its exact maturity is not a fixed
number of years) and the Real Return Bond (inflation-linked, a real yield).
"""

import json
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd

VALET_URL = "https://www.bankofcanada.ca/valet/observations/group/bond_yields_benchmark/json"

# Valet series id -> benchmark tenor in years.
BENCHMARK_SERIES = {
    "BD.CDN.2YR.DQ.YLD": 2,
    "BD.CDN.3YR.DQ.YLD": 3,
    "BD.CDN.5YR.DQ.YLD": 5,
    "BD.CDN.7YR.DQ.YLD": 7,
    "BD.CDN.10YR.DQ.YLD": 10,
}

COLUMNS = ["date", "tenor_years", "yield_rate"]


def parse_valet_observations(payload: dict) -> pd.DataFrame:
    """Turn a Valet JSON payload into a tidy table, one row per date and tenor.

    Columns: date (Timestamp), tenor_years (int), yield_rate (decimal).
    Valet reports percent ("3.37"); we convert to decimal (0.0337).
    Missing or empty values are skipped, never replaced by a guess.
    """
    rows = []
    for observation in payload.get("observations", []):
        date = pd.Timestamp(observation["d"])
        for series_id, tenor in BENCHMARK_SERIES.items():
            value = observation.get(series_id, {}).get("v")
            if value in (None, ""):
                continue
            rows.append({"date": date, "tenor_years": tenor, "yield_rate": float(value) / 100})
    table = pd.DataFrame(rows, columns=COLUMNS)
    return table.sort_values(["date", "tenor_years"]).reset_index(drop=True)


def fetch_benchmark_yields(start_date: str, end_date: str) -> pd.DataFrame:
    """Download benchmark yields between two dates (YYYY-MM-DD). Needs internet."""
    url = f"{VALET_URL}?start_date={start_date}&end_date={end_date}"
    request = Request(url, headers={"User-Agent": "cad-yield-curve-lab"})
    with urlopen(request, timeout=60) as response:
        payload = json.load(response)
    return parse_valet_observations(payload)


def save_benchmark_yields(table: pd.DataFrame, csv_path: str | Path) -> None:
    table.to_csv(csv_path, index=False, date_format="%Y-%m-%d")


def load_benchmark_yields(csv_path: str | Path) -> pd.DataFrame:
    """Load the saved CSV and check it before use (offline, reproducible)."""
    table = pd.read_csv(csv_path, parse_dates=["date"])

    missing = [col for col in COLUMNS if col not in table.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    if table[COLUMNS].isna().any().any():
        raise ValueError("Some cells are empty.")
    if not set(table["tenor_years"]).issubset(BENCHMARK_SERIES.values()):
        raise ValueError(f"Unexpected tenors: {sorted(set(table['tenor_years']))}")
    # Guard against a percent/decimal mix-up: 3.37 instead of 0.0337.
    if (table["yield_rate"].abs() > 0.5).any():
        raise ValueError("Yields above 50%: are they in percent instead of decimal?")
    if table.duplicated(["date", "tenor_years"]).any():
        raise ValueError("Duplicated (date, tenor) rows.")

    return table.sort_values(["date", "tenor_years"]).reset_index(drop=True)
