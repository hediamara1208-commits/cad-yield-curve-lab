# Project Status

_Last updated: 2026-11-12_

## Current phase

**Phase 1**: synthetic data and bond cash flows. `bond_cash_flows` is done; next is bond pricing from discount factors.

## Completed

- Conventions defined (`ASSUMPTIONS.md`).
- Synthetic dataset generated from a known reference curve (`data/`).
- Hand bootstrap of bonds A, B, C verified (see `LEARNING_NOTES.md`). A quick script confirmed that the bootstrap recovers all 5 reference zero rates.
- Project skeleton: `src/yieldcurve/`, `tests/`, `pyproject.toml`, `requirements.txt`.
- `bond_cash_flows` implemented.
- Input validation of `bond_cash_flows`: coupon_rate in [0, 0.50], maturity_years integer ≥ 1, face_value > 0. 11 tests pass.
- Local Git repository initialised, first commit made.
- `price_from_discount_factors` in `src/yieldcurve/pricing.py`: P = Σ CF(t) × DF(t). The reference curve reprices all 5 synthetic bonds within 1e-4. 15 tests pass.

- `load_bonds` in `src/yieldcurve/data.py`: loads the CSV, checks columns, empty cells, duplicate ids, positive prices, contract terms (via `bond_cash_flows`), returns bonds sorted by maturity. 23 tests pass.
- `bond_cash_flows` now accepts NumPy integers (`numbers.Integral`).

## In progress

- Branch `feature/bond-pricing` (pricing + data loader), not yet committed.

## Lessons from debugging

- `pytest.approx` does not support nested structures (list of tuples). Fix: compare times exactly and amounts with `approx` separately.
- Floating-point: `100 * 0.035 == 3.5000000000000004`. Never compare money amounts with `==`.

## Open issues

- No GitHub remote yet (local Git only).

## Next recommended tasks

1. Phase 2: `bootstrap_discount_factors` in `curve.py`. It must check that maturities are exactly 1, 2, …, N (one bond per year, no gap), since our simple bootstrap needs no interpolation.

## Architectural decisions

- `src/` layout; package `yieldcurve`. Financial logic never lives in the Dash app.
- Rates stored as decimals everywhere in code.
- Synthetic prices are derived from a known curve so that the bootstrap can be tested against a ground truth.
- Tests written before or alongside each core function.
