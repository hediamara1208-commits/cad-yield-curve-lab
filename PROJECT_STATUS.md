# Project Status

_Last updated: 2026-11-13_

## Current phase

**Phase 2 done**: the curve engine produces discount factors, zero rates and forward rates. Next is Phase 3 (first Dash app).

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

- Pricing and data loader merged into `main` (commit ea0e381).
- `bootstrap_discount_factors` in `src/yieldcurve/curve.py`: sequential solve of DF(T); rejects maturity gaps, unsorted input and non-positive DFs. Recovers the reference DFs within 1e-5 and reprices all 5 bonds to 1e-10.
- `zero_rates_from_discount_factors` in `curve.py`: z(T) = DF(T)^(-1/T) - 1 (annual compounding). Recovers the reference zero rates within 0.1 bp.
- `forward_rate` and `one_year_forward_rates` in `curve.py` (annual compounding, DF(0) = 1). Forwards: 3.00 / 3.40 / 3.80 / 4.00 / 4.05%. Chaining the forwards gives back (1+z5)^5. 38 tests pass.
- Phase 2 committed on `feature/bootstrap` (08b756a) and merged into `main`.
- `LEARNING_NOTES.md`: forward rates, no-arbitrage, forwards vs futures.

- Phase 3 step 1: static Dash page `app/app.py` (bond table, DF chart, zero + forward chart, curve values table). Engine entry point `build_curve_table` in `curve.py`. Package installed in editable mode (`pip install -e .`). 39 tests pass.

- Phase 3 committed (4812a63) and merged into `main`.
- Phase 4 step 1: `parallel_shift` in new `src/yieldcurve/risk.py` (DF → z → z + shift → DF), and `discount_factors_from_zero_rates` in `curve.py`. 50 tests pass.

## In progress

- Phase 4 step 2: `price_after_shift`, `dv01` (P(base) − P(+1 bp)) and `scenario_table` in `risk.py`. DV01 per 100 face: A 0.0094, B 0.0190, C 0.0281, D 0.0369, E 0.0454. Convexity checked: loss(+100 bp) < 100 × DV01 < gain(−100 bp). 57 tests pass.
- Phase 4 engine committed (80ec7c9).
- Phase 4 step 3: dashboard section 6 "Rate scenarios" with a shift selector (±25/50/100 bp), a base vs shifted zero curve chart, and a table: base price, new price, change, DV01, DV01 estimate, convexity gap. Checked in the browser (+100 bp: bond B 99.6241 → 97.7487). Not committed yet.
- Next: portfolio view (nominal per bond, total DV01, hedge ratio), then Phase 5 (Bank of Canada data).

## Previous (Phase 3)

- Phase 3 step 2: `cash_flow_breakdown` in `pricing.py` (tested, 41 tests pass). Bond selector + first callback in `app.py`: shows the selected bond's cash flows, DFs, present values and total. Checked in the browser: bond B total = 99.6241 = market price.

## Lessons from debugging

- `pytest.approx` does not support nested structures (list of tuples). Fix: compare times exactly and amounts with `approx` separately.
- Floating-point: `100 * 0.035 == 3.5000000000000004`. Never compare money amounts with `==`.

## Open issues

- No GitHub remote yet (local Git only).

## Next recommended tasks

1. Phase 3 step 2: first callback, e.g. a control that changes what the charts show.
2. Dark mode for the dashboard (light only for now).

## Architectural decisions

- `src/` layout; package `yieldcurve`. Financial logic never lives in the Dash app.
- Rates stored as decimals everywhere in code.
- Synthetic prices are derived from a known curve so that the bootstrap can be tested against a ground truth.
- Tests written before or alongside each core function.
