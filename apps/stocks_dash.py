# -*- coding: utf-8 -*-
"""Stocks dashboard layout."""

import locale

from app import app

from apps import utils_dash

from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc

import dash_core_components as dcc

import dash_html_components as html

from dash_table import DataTable

import plotly.express as px

from portfolio.stocks import StocksPortfolio


print("locale: ", locale.setlocale(locale.LC_ALL, utils_dash.my_locale))

stocksportfolio = StocksPortfolio()


#############################################################################
# Figures
#############################################################################

fig_portfolio_distribution = px.pie(
    stocksportfolio.current_position(),
    values="Current Value",
    names="Ticker",
    title="Porfolio Distribution (current value)",
)
fig_portfolio_distribution.update_layout(title_x=0.5)

fig_compare_prices = px.line(
    stocksportfolio.get_historical_prices(),
    y=["Adj unit price", "Close"],
    x="Date",
    title="My adjusted unit price x Historical price",
    facet_col="Ticker",
    facet_col_wrap=4,
    facet_row_spacing=0.15,
)
fig_compare_prices.update_layout(
    title_x=0.5,
    legend_title_text="Price type",
    xaxis={
        "rangeselector": {
            "buttons": [
                {"count": 1, "label": "1m", "step": "month", "stepmode": "backward"},
                {"count": 6, "label": "6m", "step": "month", "stepmode": "backward"},
                {"count": 1, "label": "YTD", "step": "year", "stepmode": "todate"},
                {"count": 1, "label": "1y", "step": "year", "stepmode": "backward"},
                {"step": "all"},
            ],
            "xanchor": "right",
            "yanchor": "top",
        },
        "rangeslider": {"visible": False},
        "type": "date",
    },
)
fig_compare_prices.update_yaxes(showticklabels=True, matches=None, visible=True)
fig_compare_prices.update_xaxes(showticklabels=True, visible=True)


#############################################################################
# Table
#############################################################################


def table_current_pos():
    column = []
    for col in stocksportfolio.current_position().columns:
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
        data=stocksportfolio.current_position().to_dict("records"),
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
                            "Stocks Portfolio Balance",
                            className="text-center font-weight-bold bg-info",
                        ),
                        dbc.ListGroup(
                            [
                                dbc.ListGroupItem(
                                    "Total amount invested:", color="secondary"
                                ),
                                dbc.ListGroupItem(
                                    locale.currency(
                                        stocksportfolio.total_invest[0], grouping=True
                                    )
                                ),
                                dbc.ListGroupItem("Current Value:", color="secondary"),
                                dbc.ListGroupItem(
                                    locale.currency(
                                        stocksportfolio.total_invest[1], grouping=True
                                    )
                                ),
                                dbc.ListGroupItem("Total Return:", color="secondary"),
                                dbc.ListGroupItem(
                                    locale.format_string(
                                        "%.2f%%", stocksportfolio.total_return
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
        dbc.Row(
            [
                dbc.Col(
                    [dcc.Graph(id="pie-fig1", figure=fig_portfolio_distribution)],
                    width={"size": 3},
                ),
                dbc.Col(
                    [dcc.Graph(id="line1-fig1", figure=fig_compare_prices)],
                    width={"size": 9},
                ),
            ],
        ),
        dbc.Row(
            [dbc.Col(html.H1(children="Current Stocks Position"), className="mb-4")]
        ),
        dbc.Row(
            [
                dbc.Col(table_current_pos()),
            ],
        ),
        dbc.Row([dbc.Col(html.H1(children="Stocks Transactions"), className="mb-4")]),
        dbc.Row(
            [
                html.Label(
                    [
                        "Choose which stock to show the transactions",
                        dcc.Dropdown(
                            id="stocks_trans",
                            options=[
                                {"label": x, "value": x}
                                for x in stocksportfolio.stockstransactions.transactions().Ticker.unique()
                            ],
                            multi=True,
                            value=stocksportfolio.stockstransactions.transactions().Ticker.unique(),
                        ),
                    ]
                ),
            ]
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="stocks_transaction_table"),
            )
        ),
    ],
    fluid=True,
)


#############################################################################
# Callbacks
#############################################################################


@app.callback(
    Output(component_id="stocks_transaction_table", component_property="children"),
    [Input(component_id="stocks_trans", component_property="value")],
)
def update_transaction_table(option_stocks):
    print("#####################")
    print("# update transaction table option_stocks: ", option_stocks)
    pd_df = stocksportfolio.stockstransactions.transactions()
    pd_df = pd_df.loc[pd_df["Ticker"].isin(option_stocks)]
    columns = []
    for col in pd_df.columns:
        col_fmt = {"name": col, "id": col}
        if col in ["Unit Price", "Operation Cost", "Adj Cost", "Adj unit price"]:
            col_fmt["format"] = utils_dash.money
            col_fmt["type"] = "numeric"
        columns.append(col_fmt)
    return DataTable(
        id="table_transaction",
        data=pd_df.to_dict("records"),
        sort_action="native",
        columns=columns,
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "rgb(248, 248, 248)"},
        ],
        style_header={"backgroundColor": "rgb(230, 230, 230)", "fontWeight": "bold"},
    )


# vim: ts=4
