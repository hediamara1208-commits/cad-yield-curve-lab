"""Download Government of Canada benchmark yields from the Bank of Canada.

Saves data/boc_benchmark_yields.csv, which the engine and dashboard read
offline. Re-run to refresh the data.

Usage (from the project root):
    .venv\\Scripts\\python.exe scripts\\download_boc_yields.py 2020-01-01 2026-11-13
"""

import sys
from pathlib import Path

from yieldcurve.boc import fetch_benchmark_yields, save_benchmark_yields

OUTPUT = Path(__file__).parent.parent / "data" / "boc_benchmark_yields.csv"


def main(start_date: str, end_date: str) -> None:
    table = fetch_benchmark_yields(start_date, end_date)
    save_benchmark_yields(table, OUTPUT)
    print(
        f"Saved {len(table)} rows, {table['date'].nunique()} dates "
        f"({table['date'].min():%Y-%m-%d} to {table['date'].max():%Y-%m-%d}) to {OUTPUT.name}"
    )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
