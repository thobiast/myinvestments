# -*- coding: utf-8 -*-
"""FII dashboard layout."""

import locale

from app import app

from apps import utils_dash

from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc

import dash_core_components as dcc

import dash_html_components as html

from dash_table import DataTable

import plotly.express as px

from portfolio.fii import FiiPortfolio


print("locale: ", locale.setlocale(locale.LC_ALL, utils_dash.my_locale))

fiiportfolio = FiiPortfolio()


#############################################################################
# Figures
#############################################################################

fig_div_rcvd_yearly = px.bar(
    fiiportfolio.total_dividend_received("Y"),
    x="Date",
    y="Amount Received",
    color="Date",
    title="Dividends Received Yearly",
)
fig_div_rcvd_yearly.update_layout(
    title_x=0.5, yaxis={"tickprefix": utils_dash.graph_money_prefix}
)

fig_div_rcvd_monthly = px.bar(
    fiiportfolio.calc_monthly_dividends(),
    x="Pay Month",
    y="Amount Received",
    color="Ticker",
    barmode="stack",
    title="Dividends Received Monthly",
)
fig_div_rcvd_monthly.update_layout(
    title_x=0.5, yaxis={"tickprefix": utils_dash.graph_money_prefix}
)
fig_div_rcvd_monthly.update_xaxes(rangeslider_visible=True)

fig_monthly_pos = px.line(
    fiiportfolio.monthly_position(),
    y="Adj Cost",
    color="Ticker",
    title="Monthly Position",
)
fig_monthly_pos.update_layout(
    title_x=0.5,
    yaxis_title="Money invested",
    yaxis={"tickprefix": utils_dash.graph_money_prefix},
)
fig_monthly_pos.update_xaxes(rangeslider_visible=True)

fig_portfolio_distribution = px.pie(
    fiiportfolio.current_position(),
    values="Adj Cost",
    names="Ticker",
    title="Porfolio Distribution",
)
fig_portfolio_distribution.update_layout(title_x=0.5)

fig_monthly_div_yield = px.line(
    fiiportfolio.calc_monthly_dividends(),
    y="Dividend Yield",
    x="Date",
    color="Ticker",
    title="Monthly Dividend Yield (%)",
)
fig_monthly_div_yield.update_layout(
    title_x=0.5,
    yaxis={"tickformat": ",.2f", "ticksuffix": "%"},
)
fig_monthly_div_yield.update_xaxes(rangeslider_visible=True)

fig_div_rcvd_ticker = px.bar(
    fiiportfolio.calc_monthly_dividends(),
    x="Ticker",
    y="Amount Received",
    color="Ticker",
    title="Dividends Received by Ticker",
)
fig_div_rcvd_ticker.update_layout(
    title_x=0.5, yaxis={"tickprefix": utils_dash.graph_money_prefix}
)

#############################################################################
# Table
#############################################################################


def table_current_pos():
    column = []
    for col in fiiportfolio.current_position().columns:
        col_fmt = {"name": col, "id": col}
        if col == "Gain/Loss Pct":
            col_fmt["format"] = utils_dash.percentage
            col_fmt["type"] = "numeric"
        if col in ["Current Quote", "Current Value", "Adj unit price", "Adj Cost"]:
            col_fmt["format"] = utils_dash.money
            col_fmt["type"] = "numeric"
        column.append(col_fmt)
    return DataTable(
        id="table",
        data=fiiportfolio.current_position().to_dict("records"),
        sort_action="native",
        columns=column,
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "rgb(248, 248, 248)"},
            {
                "if": {
                    "filter_query": "{Gain/Loss Pct} < 0",
                    "column_id": "Gain/Loss Pct",
                },
                "backgroundColor": "tomato",
            },
            {
                "if": {
                    "filter_query": "{Gain/Loss Pct} >= 0",
                    "column_id": "Gain/Loss Pct",
                },
                "backgroundColor": "dodgerblue",
            },
        ],
        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
    )


#############################################################################
# layout
#############################################################################

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Card(
                    [
                        dbc.CardHeader(
                            "FII Portfolio Balance",
                            className="text-center font-weight-bold bg-info",
                        ),
                        dbc.ListGroup(
                            [
                                dbc.ListGroupItem(
                                    "Total amount invested:", color="secondary"
                                ),
                                dbc.ListGroupItem(
                                    locale.currency(
                                        fiiportfolio.total_invest[0], grouping=True
                                    )
                                ),
                                dbc.ListGroupItem("Current Value:", color="secondary"),
                                dbc.ListGroupItem(
                                    locale.currency(
                                        fiiportfolio.total_invest[1], grouping=True
                                    )
                                ),
                                dbc.ListGroupItem(
                                    "All dividends received:", color="secondary"
                                ),
                                dbc.ListGroupItem(
                                    locale.currency(
                                        fiiportfolio.calc_monthly_dividends()[
                                            "Amount Received"
                                        ].sum(),
                                        grouping=True,
                                    )
                                ),
                                dbc.ListGroupItem(
                                    "Last month dividend yield:", color="secondary"
                                ),
                                dbc.ListGroupItem(
                                    locale.format_string(
                                        "%.2f%%", fiiportfolio.total_dividend_yield
                                    )
                                ),
                            ],
                            horizontal=True,
                            className="mb-2",
                        ),
                    ],
                ),
            ],
            justify="center",
        ),
        # Dividends received monthly
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Graph(
                            id="line1-fig1",
                            figure=fig_div_rcvd_monthly,
                        ),
                    ],
                ),
            ],
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Graph(
                            id="line1-fig2",
                            figure=fig_div_rcvd_yearly,
                        ),
                    ],
                    width={"size": 2},
                ),
                dbc.Col(
                    [dcc.Graph(id="line-fig4", figure=fig_div_rcvd_ticker)],
                    width={"size": 4},
                ),
                dbc.Col(
                    [dcc.Graph(id="line-fig3", figure=fig_monthly_div_yield)],
                    width={"size": 6},
                ),
            ],
        ),
        dbc.Row(
            [
                dbc.Col(
                    [dcc.Graph(id="line-fig2", figure=fig_monthly_pos)],
                    width={"size": 8},
                ),
                dbc.Col(
                    [dcc.Graph(id="pie-fig1", figure=fig_portfolio_distribution)],
                    width={"size": 4},
                ),
            ],
        ),
        dbc.Row([dbc.Col(html.H1(children="Current FII Position"), className="mb-4")]),
        dbc.Row(
            [
                dbc.Col(table_current_pos()),
            ],
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.H1(children="Monthly Detailed Dividends"),
                    className="mb-4",
                    style={"margin-top": "20px"},
                )
            ]
        ),
        dbc.Row(
            [
                html.Label(
                    [
                        "Choose which FII to show the detailed dividends",
                        dcc.Dropdown(
                            id="monthly_div_detailed",
                            options=[
                                {"label": x, "value": x}
                                for x in fiiportfolio.fiitransactions.transactions().Ticker.unique()
                            ],
                            multi=True,
                            value=fiiportfolio.fiitransactions.transactions().Ticker.unique(),
                        ),
                    ]
                ),
            ],
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="monthly_div_details_table"),
            )
        ),
        dbc.Row([dbc.Col(html.H1(children="FII Transactions"), className="mb-4")]),
        dbc.Row(
            [
                html.Label(
                    [
                        "Choose which FII to show the transactions",
                        dcc.Dropdown(
                            id="fii_trans",
                            options=[
                                {"label": x, "value": x}
                                for x in fiiportfolio.fiitransactions.transactions().Ticker.unique()
                            ],
                            multi=True,
                            value=fiiportfolio.fiitransactions.transactions().Ticker.unique(),
                        ),
                    ]
                ),
            ]
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="transaction_table"),
            )
        ),
    ],
    fluid=True,
)


#############################################################################
# Callbacks
#############################################################################


@app.callback(
    Output(component_id="monthly_div_details_table", component_property="children"),
    [Input(component_id="monthly_div_detailed", component_property="value")],
)
def update_monthly_div_details_table(option_fiis):
    print("#####################")
    print("# update div_details_table option_fiis: ", option_fiis)
    pd_df = fiiportfolio.calc_monthly_dividends(sort_date_ascending=False).drop(
        ["year", "month"], axis="columns"
    )
    pd_df = pd_df.loc[pd_df["Ticker"].isin(option_fiis)]

    columns = []
    for col in pd_df.columns:
        col_fmt = {"name": col, "id": col}
        if col in ["Dividend Yield", "Dividend Yield on Cost"]:
            col_fmt["format"] = utils_dash.percentage
            col_fmt["type"] = "numeric"
        if col in [
            "Adj Cost",
            "Adj unit price",
            "Monthly Dividends",
            "Amount Received",
            "Current Quote",
        ]:
            col_fmt["format"] = utils_dash.money
            col_fmt["type"] = "numeric"
        columns.append(col_fmt)

    return DataTable(
        id="table_monthly_div_detail",
        data=pd_df.to_dict("records"),
        sort_action="native",
        columns=columns,
        page_size=20,
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "rgb(248, 248, 248)"},
        ],
        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
    )


@app.callback(
    Output(component_id="transaction_table", component_property="children"),
    [Input(component_id="fii_trans", component_property="value")],
)
def update_transaction_table(option_fiis):
    print("#####################")
    print("# update transaction table option_fiis: ", option_fiis)
    pd_df = fiiportfolio.fiitransactions.transactions()
    pd_df = pd_df.loc[pd_df["Ticker"].isin(option_fiis)]
    columns = []
    for col in pd_df.columns:
        col_fmt = {"name": col, "id": col}
        if col in ["Unit Price", "Operation Cost", "Adj Cost", "Adj unit price"]:
            col_fmt["format"] = utils_dash.money
            col_fmt["type"] = "numeric"
        columns.append(col_fmt)
    return DataTable(
        id="table_transaction",
        data=pd_df.sort_index(ascending=True).to_dict("records"),
        sort_action="native",
        columns=columns,
        page_size=20,
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "rgb(248, 248, 248)"},
        ],
        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
    )


# vim: ts=4
