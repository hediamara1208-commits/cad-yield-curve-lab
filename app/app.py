"""CAD Yield Curve Lab: Dash dashboard (curves, price breakdown, rate scenarios).

The app does NO finance itself. It calls the tested engine (yieldcurve),
then only formats and draws the results.

Run from the project root:
    .venv\\Scripts\\python.exe app\\app.py
then open http://127.0.0.1:8050
"""

from pathlib import Path

import plotly.graph_objects as go
from dash import Dash, Input, Output, callback, dcc, html

from yieldcurve.boc import load_benchmark_yields
from yieldcurve.curve import build_curve_table, zero_rates_from_discount_factors
from yieldcurve.data import load_bonds
from yieldcurve.market import compare_curves, slope_bp
from yieldcurve.instruments import bond_cash_flows
from yieldcurve.pricing import cash_flow_breakdown
from yieldcurve.risk import (
    STANDARD_SHIFTS_BP,
    dv01,
    hedge_nominal,
    parallel_shift,
    portfolio_risk,
    scenario_table,
)

DATA_FILE = Path(__file__).parent.parent / "data" / "synthetic_bonds.csv"
BOC_FILE = Path(__file__).parent.parent / "data" / "boc_benchmark_yields.csv"

# Chart colors: validated categorical slots 1 and 2 (light surface).
ZERO_COLOR = "#2a78d6"     # blue
FORWARD_COLOR = "#eb6834"  # orange
SURFACE = "#fcfcfb"
TEXT_PRIMARY = "#0b0b0b"
TEXT_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"


# ---------------------------------------------------------------- engine call
bonds = load_bonds(DATA_FILE)
curve = build_curve_table(bonds)
discount_factors = dict(zip(curve["maturity_years"], curve["discount_factor"]))

# Observed Bank of Canada benchmark yields (saved CSV, not live).
market = load_benchmark_yields(BOC_FILE)
market_slope = slope_bp(market)  # 2s10s in bp
FIRST_MARKET_DATE = market["date"].min()
LAST_MARKET_DATE = market["date"].max()

# Example portfolio from the learning notes: 1 M$ of A and 1 M$ of E.
DEFAULT_NOMINALS = {"A": 1_000_000, "E": 1_000_000}


# ---------------------------------------------------------------- figures
def apply_chart_style(figure: go.Figure, y_title: str) -> go.Figure:
    figure.update_layout(
        plot_bgcolor=SURFACE,
        paper_bgcolor=SURFACE,
        font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=TEXT_PRIMARY, size=13),
        margin=dict(l=60, r=90, t=20, b=50),
        height=340,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.08, x=0),
    )
    figure.update_xaxes(
        title="Maturity (years)", dtick=1, showgrid=False,
        linecolor=AXIS, tickfont=dict(color=TEXT_MUTED),
    )
    figure.update_yaxes(
        title=y_title, gridcolor=GRID, zeroline=False,
        linecolor=AXIS, tickfont=dict(color=TEXT_MUTED),
    )
    return figure


def discount_factor_figure() -> go.Figure:
    # Add t = 0 with DF(0) = 1: one dollar today is worth one dollar.
    maturities = [0] + curve["maturity_years"].tolist()
    discount_factors = [1.0] + curve["discount_factor"].tolist()

    figure = go.Figure(
        go.Scatter(
            x=maturities, y=discount_factors, mode="lines+markers",
            line=dict(color=ZERO_COLOR, width=2), marker=dict(size=8),
            name="Discount factor",
            hovertemplate="DF(%{x}) = %{y:.6f}<extra></extra>",
        )
    )
    return apply_chart_style(figure, "Discount factor")


def rates_figure() -> go.Figure:
    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=curve["maturity_years"], y=curve["zero_rate"], mode="lines+markers",
            line=dict(color=ZERO_COLOR, width=2), marker=dict(size=8),
            name="Zero rate z(T)",
            hovertemplate="Zero rate: %{y:.2%}<extra></extra>",
        )
    )

    # A one-year forward f(T-1, T) applies over the whole year: draw it as a step.
    step_x = curve["forward_start"].tolist() + [curve["maturity_years"].iloc[-1]]
    step_y = curve["forward_rate"].tolist() + [curve["forward_rate"].iloc[-1]]
    figure.add_trace(
        go.Scatter(
            x=step_x, y=step_y, mode="lines", line_shape="hv",
            line=dict(color=FORWARD_COLOR, width=2, dash="dash"),
            name="1-year forward f(T-1, T)",
            hovertemplate="Forward from year %{x}: %{y:.2%}<extra></extra>",
        )
    )

    # Direct labels at the right end, in text ink (not series color).
    last = curve.iloc[-1]
    for label, value in [("Zero", last["zero_rate"]), ("Forward", last["forward_rate"])]:
        figure.add_annotation(
            x=last["maturity_years"], y=value, text=f"{label} {value:.2%}",
            xanchor="left", xshift=8, showarrow=False, font=dict(color=TEXT_PRIMARY, size=12),
        )

    figure = apply_chart_style(figure, "Rate (annual compounding)")
    figure.update_yaxes(tickformat=".1%")
    return figure


# ---------------------------------------------------------------- tables
def bonds_table() -> html.Table:
    header = ["Bond", "Maturity (years)", "Annual coupon", "Face value", "Price"]
    rows = [
        [b.bond_id, b.maturity_years, f"{b.coupon_rate:.2%}", f"{b.face_value:.0f}", f"{b.price:.4f}"]
        for b in bonds.itertuples()
    ]
    return make_table(header, rows)


def curve_values_table() -> html.Table:
    header = ["Maturity (years)", "Discount factor", "Zero rate", "Forward f(T-1, T)"]
    rows = [
        [int(r.maturity_years), f"{r.discount_factor:.6f}", f"{r.zero_rate:.4%}", f"{r.forward_rate:.4%}"]
        for r in curve.itertuples()
    ]
    return make_table(header, rows)


def make_table(header: list[str], rows: list[list]) -> html.Table:
    return html.Table(
        className="data-table",
        children=[
            html.Thead(html.Tr([html.Th(h) for h in header])),
            html.Tbody([html.Tr([html.Td(cell) for cell in row]) for row in rows]),
        ],
    )


# ---------------------------------------------------------------- layout
app = Dash(__name__, title="CAD Yield Curve Lab")

app.layout = html.Main(
    className="page",
    children=[
        html.H1("CAD Yield Curve Lab"),
        html.P(
            className="notice",
            children=(
                "Synthetic educational data, not market quotes. "
                "Annual coupons, annual compounding, valuation on a coupon date. "
                "See ASSUMPTIONS.md."
            ),
        ),
        html.H2("1. Input: bond prices"),
        bonds_table(),
        html.H2("2. Bootstrapped discount factors"),
        html.P("DF(T) is the value today of 1 $ received in T years.", className="caption"),
        dcc.Graph(figure=discount_factor_figure(), config={"displayModeBar": False}),
        html.H2("3. Zero rates and forward rates"),
        html.P(
            "Rising zero curve: each 1-year forward sits above the zero rate, "
            "since the zero rate is an average of the forwards.",
            className="caption",
        ),
        dcc.Graph(figure=rates_figure(), config={"displayModeBar": False}),
        html.H2("4. Curve values"),
        curve_values_table(),
        html.H2("5. Price of one bond, flow by flow"),
        html.P("Choose a bond: its price is the sum of its discounted cash flows.", className="caption"),
        dcc.Dropdown(
            id="bond-selector",
            options=[{"label": f"Bond {b}", "value": b} for b in bonds["bond_id"]],
            value="C",
            clearable=False,
            style={"maxWidth": "240px"},
        ),
        html.Div(id="breakdown-output", style={"marginTop": "12px"}),
        html.H2("6. Rate scenarios: parallel shift of the zero curve"),
        html.P(
            "Every zero rate moves by the same number of basis points (1 bp = 0.01%). "
            "Each bond is fully repriced on the shifted curve.",
            className="caption",
        ),
        dcc.RadioItems(
            id="shift-selector",
            options=[{"label": f"{s:+d} bp", "value": s} for s in STANDARD_SHIFTS_BP],
            value=25,
            inline=True,
            className="shift-selector",
        ),
        dcc.Graph(id="shift-chart", config={"displayModeBar": False}),
        html.Div(id="scenario-output"),
        html.H2("7. Portfolio risk and DV01 hedge"),
        html.P(
            "Enter the face amount held in each bond ($). DV01 and P&L are in dollars, "
            "under the shift selected in section 6. A negative amount is a short position.",
            className="caption",
        ),
        html.Div(
            className="nominal-inputs",
            children=[
                html.Label([
                    f"Bond {bond_id}",
                    dcc.Input(
                        # step="any": accept any amount (a numeric step makes the browser
                        # reject values that are not multiples of it, e.g. 1,950,000).
                        id=f"nominal-{bond_id}", type="number", step="any",
                        value=DEFAULT_NOMINALS.get(bond_id, 0), debounce=True,
                    ),
                ])
                for bond_id in bonds["bond_id"]
            ],
        ),
        html.Label(["Hedge with bond ", dcc.Dropdown(
            id="hedge-selector",
            options=[{"label": f"Bond {b}", "value": b} for b in bonds["bond_id"]],
            value="C", clearable=False, style={"width": "160px", "display": "inline-block"},
        )], className="hedge-label"),
        html.Div(id="portfolio-output", style={"marginTop": "12px"}),
        html.H2("8. Observed market: Government of Canada benchmark yields"),
        html.P(
            className="notice",
            children=(
                f"Observed data from the Bank of Canada (Valet API), "
                f"{FIRST_MARKET_DATE:%Y-%m-%d} to {LAST_MARKET_DATE:%Y-%m-%d}. Not live. "
                "These are yields to maturity of benchmark coupon bonds, not zero rates, "
                "and they are not used by the synthetic bootstrap above."
            ),
        ),
        html.Div(
            className="date-pickers",
            children=[
                html.Label(["First date", dcc.DatePickerSingle(
                    id="first-date", date="2023-06-30", display_format="YYYY-MM-DD",
                    min_date_allowed=FIRST_MARKET_DATE, max_date_allowed=LAST_MARKET_DATE,
                )]),
                html.Label(["Second date", dcc.DatePickerSingle(
                    id="second-date", date=f"{LAST_MARKET_DATE:%Y-%m-%d}", display_format="YYYY-MM-DD",
                    min_date_allowed=FIRST_MARKET_DATE, max_date_allowed=LAST_MARKET_DATE,
                )]),
            ],
        ),
        dcc.Graph(id="observed-curves", config={"displayModeBar": False}),
        html.Div(id="observed-comparison"),
        html.H2("9. Curve slope over time: 10-year minus 2-year (2s10s)"),
        html.P(
            "Above zero: upward-sloping curve. Below zero: inverted curve "
            "(2-year yield higher than 10-year yield).",
            className="caption",
        ),
        dcc.Graph(id="slope-history", config={"displayModeBar": False}),
    ],
)


# ---------------------------------------------------------------- callbacks
@callback(
    Output("breakdown-output", "children"),  # what changes: the content of this Div
    Input("bond-selector", "value"),         # what triggers it: the dropdown value
)
def show_breakdown(bond_id: str):
    # 1. Find the selected bond.
    bond = bonds[bonds["bond_id"] == bond_id].iloc[0]

    # 2. Ask the engine for its cash flows and their present values.
    cash_flows = bond_cash_flows(bond["face_value"], bond["coupon_rate"], bond["maturity_years"])
    breakdown = cash_flow_breakdown(cash_flows, discount_factors)

    # 3. Format only: no financial calculation here.
    header = ["Year", "Cash flow", "Discount factor", "Present value"]
    rows = [
        [row["time"], f"{row['cash_flow']:.2f}", f"{row['discount_factor']:.6f}", f"{row['present_value']:.4f}"]
        for row in breakdown
    ]
    model_price = sum(row["present_value"] for row in breakdown)
    rows.append(["Total (model price)", "", "", f"{model_price:.4f}"])

    return html.Div(
        [
            make_table(header, rows),
            html.P(
                f"Market price of bond {bond_id}: {bond['price']:.4f}. "
                "The curve was built from these prices, so the two match.",
                className="caption",
                style={"marginTop": "8px"},
            ),
        ]
    )


@callback(
    Output("shift-chart", "figure"),
    Output("scenario-output", "children"),
    Input("shift-selector", "value"),
)
def show_scenario(shift_bp: int):
    # 1. Engine: shifted curve and repriced bonds.
    shifted_zero_rates = zero_rates_from_discount_factors(parallel_shift(discount_factors, shift_bp))
    scenario = scenario_table(bonds, discount_factors, [shift_bp])
    change_column = f"change_{shift_bp:+g}bp"

    # 2. Chart: base vs shifted zero curve.
    maturities = curve["maturity_years"].tolist()
    figure = go.Figure()
    figure.add_trace(go.Scatter(
        x=maturities, y=curve["zero_rate"], mode="lines+markers", name="Base zero curve",
        line=dict(color=ZERO_COLOR, width=2), marker=dict(size=8),
        hovertemplate="Base: %{y:.2%}<extra></extra>",
    ))
    figure.add_trace(go.Scatter(
        x=maturities, y=[shifted_zero_rates[m] for m in maturities], mode="lines+markers",
        name=f"Shifted {shift_bp:+d} bp",
        line=dict(color=FORWARD_COLOR, width=2, dash="dash"), marker=dict(size=8),
        hovertemplate="Shifted: %{y:.2%}<extra></extra>",
    ))
    figure = apply_chart_style(figure, "Zero rate (annual compounding)")
    figure.update_yaxes(tickformat=".1%")

    # 3. Table: full repricing vs the linear DV01 estimate.
    header = [
        "Bond", "Maturity", "Base price", "New price", "Price change",
        "DV01 (per 100)", "DV01 estimate", "Convexity gap",
    ]
    rows = []
    for r in scenario.to_dict("records"):  # one dict per bond
        change = r[change_column]
        linear_estimate = -r["dv01"] * shift_bp  # rates up -> price down
        rows.append([
            r["bond_id"], r["maturity_years"], f"{r['base_price']:.4f}",
            f"{r['base_price'] + change:.4f}", f"{change:+.4f}", f"{r['dv01']:.4f}",
            f"{linear_estimate:+.4f}", f"{change - linear_estimate:+.4f}",
        ])

    note = html.P(
        "DV01 estimate = −DV01 × shift (a straight-line approximation). "
        "Convexity gap = price change − DV01 estimate: always positive, because the "
        "price falls less (or rises more) than the straight line predicts.",
        className="caption", style={"marginTop": "8px"},
    )
    return figure, html.Div([make_table(header, rows), note])


PORTFOLIO_INPUTS = (
    [Input(f"nominal-{bond_id}", "value") for bond_id in bonds["bond_id"]]  # one per bond
    + [Input("hedge-selector", "value"), Input("shift-selector", "value")]
)


@callback(Output("portfolio-output", "children"), *PORTFOLIO_INPUTS)
def show_portfolio(*args):
    *nominal_values, hedge_bond_id, shift_bp = args
    nominals = {
        bond_id: float(value or 0) for bond_id, value in zip(bonds["bond_id"], nominal_values)
    }

    # 1. Engine: position risk and hedge size.
    positions = portfolio_risk(bonds, discount_factors, nominals, shift_bp)
    if positions.empty:
        return html.P("Enter at least one non-zero position.", className="caption")

    total_dv01 = positions["dv01"].sum()
    hedge = bonds[bonds["bond_id"] == hedge_bond_id].iloc[0]
    hedge_flows = bond_cash_flows(hedge["face_value"], hedge["coupon_rate"], hedge["maturity_years"])
    hedge_dv01_per_100 = dv01(hedge_flows, discount_factors)
    nominal_to_sell = hedge_nominal(total_dv01, hedge_dv01_per_100)

    # 2. Format only.
    header = ["Bond", "Face amount ($)", "Market value ($)", "DV01 ($)", f"P&L at {shift_bp:+d} bp ($)"]
    rows = [
        [r["bond_id"], f"{r['nominal']:,.0f}", f"{r['market_value']:,.0f}",
         f"{r['dv01']:,.0f}", f"{r['pnl']:+,.0f}"]
        for r in positions.to_dict("records")
    ]
    rows.append([
        "Total", f"{positions['nominal'].sum():,.0f}", f"{positions['market_value'].sum():,.0f}",
        f"{total_dv01:,.0f}", f"{positions['pnl'].sum():+,.0f}",
    ])

    hedge_text = html.P(
        f"To bring the portfolio DV01 of {total_dv01:,.0f} $ to zero, sell about "
        f"{nominal_to_sell:,.0f} $ face of bond {hedge_bond_id} "
        f"(DV01 {hedge_dv01_per_100:.4f} per 100 face). "
        "This hedge only covers small parallel shifts.",
        className="caption", style={"marginTop": "8px"},
    )
    return html.Div([make_table(header, rows), hedge_text])


@callback(
    Output("observed-curves", "figure"),
    Output("observed-comparison", "children"),
    Output("slope-history", "figure"),
    Input("first-date", "date"),
    Input("second-date", "date"),
)
def show_observed_market(first_date: str, second_date: str):
    # 1. Engine: curves on both dates (falls back to the last business day).
    comparison = compare_curves(market, first_date, second_date)
    first_used = comparison.attrs["first_date"]
    second_used = comparison.attrs["second_date"]
    tenors = comparison["tenor_years"].tolist()

    # 2. Observed curves chart.
    curves = go.Figure()
    for column, label, color, dash in [
        ("first_yield", f"{first_used:%Y-%m-%d}", ZERO_COLOR, "solid"),
        ("second_yield", f"{second_used:%Y-%m-%d}", FORWARD_COLOR, "dash"),
    ]:
        curves.add_trace(go.Scatter(
            x=tenors, y=comparison[column], mode="lines+markers", name=label,
            line=dict(color=color, width=2, dash=dash), marker=dict(size=8),
            hovertemplate=label + ": %{y:.2%}<extra></extra>",
        ))
    curves = apply_chart_style(curves, "Yield to maturity (observed)")
    curves.update_xaxes(title="Benchmark term (years)", tickvals=tenors)
    curves.update_yaxes(tickformat=".1%")

    # 3. Comparison table.
    header = ["Term (years)", f"{first_used:%Y-%m-%d}", f"{second_used:%Y-%m-%d}", "Change (bp)"]
    rows = [
        [int(r["tenor_years"]), f"{r['first_yield']:.2%}", f"{r['second_yield']:.2%}", f"{r['change_bp']:+.0f}"]
        for r in comparison.to_dict("records")
    ]
    first_slope = market_slope.loc[first_used]
    second_slope = market_slope.loc[second_used]
    rows.append(["2s10s slope (bp)", f"{first_slope:+.0f}", f"{second_slope:+.0f}", f"{second_slope - first_slope:+.0f}"])

    # 4. Slope history, with the two selected dates marked.
    slope = go.Figure(go.Scatter(
        x=market_slope.index, y=market_slope.values, mode="lines", name="2s10s",
        line=dict(color=ZERO_COLOR, width=2),
        hovertemplate="%{x|%Y-%m-%d}: %{y:+.0f} bp<extra></extra>",
    ))
    slope.add_hline(y=0, line=dict(color=AXIS, width=1))
    for used in (first_used, second_used):
        slope.add_vline(x=used, line=dict(color=TEXT_MUTED, width=1, dash="dot"))
        value = market_slope.loc[used]
        slope.add_annotation(
            x=used, y=value, text=f"{value:+.0f} bp",
            # Label away from the line: below a negative value, above a positive one.
            showarrow=True, arrowhead=0, ax=0, ay=36 if value < 0 else -36,
            font=dict(color=TEXT_PRIMARY, size=12), bgcolor=SURFACE,
        )
    slope = apply_chart_style(slope, "10-year minus 2-year (bp)")
    slope.update_xaxes(title="Date", dtick=None)
    slope.update_layout(showlegend=False)

    return curves, make_table(header, rows), slope


if __name__ == "__main__":
    app.run(debug=True)
