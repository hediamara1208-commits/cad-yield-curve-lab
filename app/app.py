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

from yieldcurve.curve import build_curve_table, zero_rates_from_discount_factors
from yieldcurve.data import load_bonds
from yieldcurve.instruments import bond_cash_flows
from yieldcurve.pricing import cash_flow_breakdown
from yieldcurve.risk import STANDARD_SHIFTS_BP, parallel_shift, scenario_table

DATA_FILE = Path(__file__).parent.parent / "data" / "synthetic_bonds.csv"

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


if __name__ == "__main__":
    app.run(debug=True)
