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

## In progress

- Nothing.

## Lessons from debugging

- `pytest.approx` does not support nested structures (list of tuples). Fix: compare times exactly and amounts with `approx` separately.
- Floating-point: `100 * 0.035 == 3.5000000000000004`. Never compare money amounts with `==`.

## Open issues

- No GitHub remote yet (local Git only).

## Next recommended tasks

1. Implement `bond_price_from_discount_factors` (P = sum CF × DF) and test it against the dataset.
2. Load and validate `data/synthetic_bonds.csv`.
3. Phase 2: `bootstrap_discount_factors`.

## Architectural decisions

- `src/` layout; package `yieldcurve`. Financial logic never lives in the Dash app.
- Rates stored as decimals everywhere in code.
- Synthetic prices are derived from a known curve so that the bootstrap can be tested against a ground truth.
- Tests written before or alongside each core function.
