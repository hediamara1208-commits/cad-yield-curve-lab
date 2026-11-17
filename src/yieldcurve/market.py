"""Observed market analysis on Bank of Canada benchmark yields.

Input: the tidy table from boc.load_benchmark_yields
(columns date, tenor_years, yield_rate in decimal).

All outputs describe OBSERVED yields to maturity, not model outputs and
not zero rates. Differences are reported in basis points (1 bp = 0.0001).
"""

import pandas as pd

BASIS_POINT = 0.0001


def available_date_on_or_before(table: pd.DataFrame, requested_date: str) -> pd.Timestamp:
    """Latest date with data on or before requested_date.

    Weekends and holidays have no observation: a Saturday falls back to the
    Friday before. Raises if the date is before the first observation.
    """
    requested = pd.Timestamp(requested_date)
    dates = table.loc[table["date"] <= requested, "date"]
    if dates.empty:
        raise ValueError(
            f"No data on or before {requested:%Y-%m-%d}; "
            f"first observation is {table['date'].min():%Y-%m-%d}."
        )
    return dates.max()


def curve_on_date(table: pd.DataFrame, requested_date: str) -> tuple[pd.Timestamp, pd.Series]:
    """Return (date actually used, yields indexed by tenor_years)."""
    used_date = available_date_on_or_before(table, requested_date)
    curve = table[table["date"] == used_date].set_index("tenor_years")["yield_rate"]
    return used_date, curve.sort_index()


def compare_curves(table: pd.DataFrame, first_date: str, second_date: str) -> pd.DataFrame:
    """Yields on two dates and the change in bp, one row per tenor.

    Columns: tenor_years, first_yield, second_yield, change_bp
    (change_bp = (second - first) / 1 bp). Only tenors present on both dates.
    """
    first_used, first_curve = curve_on_date(table, first_date)
    second_used, second_curve = curve_on_date(table, second_date)
    both = pd.concat({"first_yield": first_curve, "second_yield": second_curve}, axis=1).dropna()
    both["change_bp"] = (both["second_yield"] - both["first_yield"]) / BASIS_POINT
    both.attrs["first_date"] = first_used
    both.attrs["second_date"] = second_used
    return both.reset_index()


def slope_bp(table: pd.DataFrame, short_tenor: int = 2, long_tenor: int = 10) -> pd.Series:
    """Curve slope over time: long yield minus short yield, in bp (e.g. the 2s10s).

    Positive = upward-sloping curve; negative = inverted curve.
    Dates where either tenor is missing are dropped.
    """
    wide = table.pivot(index="date", columns="tenor_years", values="yield_rate")
    slope = (wide[long_tenor] - wide[short_tenor]) / BASIS_POINT
    return slope.dropna().rename(f"slope_{short_tenor}s{long_tenor}s_bp")
