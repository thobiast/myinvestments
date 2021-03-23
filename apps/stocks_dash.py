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

fig_portfolio_distribution_broker = px.pie(
    stocksportfolio.total_invest("Broker")[1],
    values="Current Value",
    names=stocksportfolio.total_invest("Broker")[1].index,
    title="Porfolio Distribution by Broker (current value)",
)
fig_portfolio_distribution_broker.update_layout(title_x=0.5)

fig_portfolio_distribution_exchange = px.pie(
    stocksportfolio.total_invest("Stock Exchange")[1],
    values="Current Value",
    names=stocksportfolio.total_invest("Stock Exchange")[1].index,
    title="Porfolio Distribution by Exchange (current value)",
)
fig_portfolio_distribution_exchange.update_layout(title_x=0.5)

fig_position_by_ticker = px.line(
    stocksportfolio.get_historical_prices(),
    y="Position updated",
    x="Date",
    color="Ticker",
    title="Ticker position",
)
fig_position_by_ticker.update_layout(
    title_x=0.5, yaxis={"tickprefix": utils_dash.graph_money_prefix}
)
fig_position_by_ticker.update_layout(
    title_x=0.5,
    xaxis={
        "rangeselector": {
            "buttons": [
                {"count": 1, "label": "1m", "step": "month", "stepmode": "backward"},
                {"count": 6, "label": "6m", "step": "month", "stepmode": "backward"},
                {"count": 1, "label": "YTD", "step": "year", "stepmode": "todate"},
                {"count": 1, "label": "1y", "step": "year", "stepmode": "backward"},
                {"count": 2, "label": "2y", "step": "year", "stepmode": "backward"},
                {"count": 5, "label": "5y", "step": "year", "stepmode": "backward"},
                {"step": "all"},
            ],
        },
        "rangeslider": {"visible": False},
        "type": "date",
    },
)


fig_dividends = px.bar(
    stocksportfolio.dividends_received("Month"),
    y="Dividends",
    x="Month",
    color="Ticker",
    title="Monthly Dividends",
)
fig_dividends.update_xaxes(rangeslider_visible=True)
fig_dividends.update_layout(
    title_x=0.5, yaxis={"tickprefix": utils_dash.graph_money_prefix}
)

fig_div_rcvd_yearly = px.bar(
    stocksportfolio.dividends_received("Year"),
    x="Year",
    y="Dividends",
    color="Ticker",
    title="Dividends Received Yearly",
)
fig_div_rcvd_yearly.update_layout(
    title_x=0.5, yaxis={"tickprefix": utils_dash.graph_money_prefix}
)


fig_compare_prices = px.line(
    stocksportfolio.get_historical_prices(),
    y=["Adj unit price", "Close"],
    x="Date",
    title="My adjusted unit price x Historical price",
    facet_col="Ticker",
    facet_col_wrap=6,
    facet_row_spacing=0.15,
    facet_col_spacing=0.05,
    height=800,
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
            "yanchor": "bottom",
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
                                        stocksportfolio.total_invest()[0], grouping=True
                                    )
                                ),
                                dbc.ListGroupItem("Current Value:", color="secondary"),
                                dbc.ListGroupItem(
                                    locale.currency(
                                        stocksportfolio.total_invest()[1], grouping=True
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
                    [
                        dcc.Graph(
                            id="fig_portfolio_distribution_id",
                            figure=fig_portfolio_distribution,
                        )
                    ],
                    width={"size": 5},
                ),
                dbc.Col(
                    [
                        dcc.Graph(
                            id="fig_portfolio_distribution_broker_id",
                            figure=fig_portfolio_distribution_broker,
                        )
                    ],
                    width={"size": 3},
                ),
                dbc.Col(
                    [
                        dcc.Graph(
                            id="fig_portfolio_distribution_exchange_id",
                            figure=fig_portfolio_distribution_exchange,
                        )
                    ],
                    width={"size": 3},
                ),
            ],
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Graph(
                            id="fig_position_by_ticker_id",
                            figure=fig_position_by_ticker,
                        )
                    ],
                ),
            ],
        ),
        dbc.Row(
            [
                dbc.Col(
                    [dcc.Graph(id="fig_div_yearly_id", figure=fig_div_rcvd_yearly)],
                    width={"size": 4},
                ),
                dbc.Col(
                    [dcc.Graph(id="figdividends_id", figure=fig_dividends)],
                    width={"size": 8},
                ),
            ],
        ),
        dbc.Row(
            [
                dbc.Col(
                    [dcc.Graph(id="fig_compare_prices_id", figure=fig_compare_prices)],
                ),
            ],
            className="h-100",
        ),
        dbc.Row(
            [dbc.Col(html.H1(children="Current Stocks Position"), className="mb-4")]
        ),
        dbc.Row(
            [
                dbc.Col(table_current_pos()),
            ],
        ),
        dbc.Row([dbc.Col(html.H1(children="Dividends"), className="mb-4")]),
        dbc.Row(
            [
                html.Label(
                    [
                        "Choose which stocks to show the detailed dividends",
                        dcc.Dropdown(
                            id="dividends_table_input",
                            options=[
                                {"label": x, "value": x}
                                for x in stocksportfolio.stockstransactions.transactions().Ticker.unique()
                            ],
                            multi=True,
                            value=stocksportfolio.stockstransactions.transactions().Ticker.unique(),
                        ),
                    ]
                ),
            ],
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="dividends_table"),
            )
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
    Output(component_id="dividends_table", component_property="children"),
    [Input(component_id="dividends_table_input", component_property="value")],
)
def update_dividends_table(option_stocks):
    print("#####################")
    print("# update div_details_table option_stocks: ", option_stocks)
    pd_df = stocksportfolio.get_dividends()
    pd_df.sort_values(by=["date", "Ticker"], ascending=[False, True], inplace=True)
    pd_df = pd_df.loc[pd_df["Ticker"].isin(option_stocks)]

    columns = []
    for col in pd_df.columns:
        col_fmt = {"name": col, "id": col}
        if col in ["value", "Dividends"]:
            col_fmt["format"] = utils_dash.money
            col_fmt["type"] = "numeric"
        columns.append(col_fmt)

    return DataTable(
        id="dividends_table_id",
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
