# CAD Yield Curve Lab

An educational Python project that bootstraps an interest rate yield curve from bond prices, derives discount factors, zero-coupon rates and forward rates, and (later) visualises them in a Dash dashboard, with a focus on Canadian fixed-income markets.

> **Status:** early development (Phase 1). The current data is **synthetic**: it is not market data.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## Documentation

- [ASSUMPTIONS.md](ASSUMPTIONS.md): modelling conventions and simplifications
- [PROJECT_STATUS.md](PROJECT_STATUS.md): development log
- [LEARNING_NOTES.md](LEARNING_NOTES.md): concepts and worked examples
