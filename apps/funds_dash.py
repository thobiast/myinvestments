# -*- coding: utf-8 -*-
"""Funds dashboard layout."""

import locale

from app import app

from apps import utils_dash

from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc

import dash_core_components as dcc

import dash_html_components as html

from dash_table import DataTable

import plotly.express as px

from portfolio.funds import FundsPortfolio


print("locale: ", locale.setlocale(locale.LC_ALL, utils_dash.my_locale))

fundsportfolio = FundsPortfolio()


#############################################################################
# Figures
#############################################################################

fig_portfolio_distribution = px.pie(
    fundsportfolio.current_position_by_cnpj(),
    values="Current Position",
    names="Fund Name",
    title="Porfolio Distribution (current value)",
)
fig_portfolio_distribution.update_layout(title_x=0.5)

fig_position_by_fund = px.line(
    fundsportfolio.historical_df,
    y="Historical Position",
    x="Date",
    color="Fund Name",
    hover_data=["Adj Value", "Valor Cota"],
    hover_name="Fund Name",
    title="Daily Fund Position",
)
fig_position_by_fund.update_layout(
    title_x=0.5, yaxis={"tickprefix": utils_dash.graph_money_prefix}
)
fig_position_by_fund.update_layout(
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


#############################################################################
# Table
#############################################################################


def table_current_pos():
    column = []
    for col in fundsportfolio.current_position_by_cnpj().columns:
        col_fmt = {"name": col, "id": col}
        if col == "Gain/Loss Pct":
            col_fmt["format"] = utils_dash.percentage
            col_fmt["type"] = "numeric"
        if col in ["Adj Value", "Current Position"]:
            col_fmt["format"] = utils_dash.money
            col_fmt["type"] = "numeric"
        column.append(col_fmt)
    return DataTable(
        id="table",
        data=fundsportfolio.current_position_by_cnpj().to_dict("records"),
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
                            "Funds Portfolio Balance",
                            className="text-center font-weight-bold bg-info",
                        ),
                        dbc.ListGroup(
                            [
                                dbc.ListGroupItem(
                                    "Total amount invested:", color="secondary"
                                ),
                                dbc.ListGroupItem(
                                    locale.currency(
                                        fundsportfolio.total_invest[0], grouping=True
                                    )
                                ),
                                dbc.ListGroupItem("Current Value:", color="secondary"),
                                dbc.ListGroupItem(
                                    locale.currency(
                                        fundsportfolio.total_invest[1], grouping=True
                                    )
                                ),
                                dbc.ListGroupItem("Total Return:", color="secondary"),
                                dbc.ListGroupItem(
                                    locale.format_string(
                                        "%.2f%%", fundsportfolio.total_return
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
                    width={"size": 4},
                ),
                dbc.Col(
                    [
                        dcc.Graph(
                            id="fig_position_by_fund_id",
                            figure=fig_position_by_fund,
                        )
                    ],
                    width={"size": 8},
                ),
            ],
        ),
        dbc.Row(
            [dbc.Col(html.H1(children="Current Funds Position"), className="mb-4")]
        ),
        dbc.Row(
            [
                dbc.Col(table_current_pos()),
            ],
        ),
        dbc.Row([dbc.Col(html.H1(children="Funds Transactions"), className="mb-4")]),
        dbc.Row(
            [
                html.Label(
                    [
                        "Choose which fund to show the transactions",
                        dcc.Dropdown(
                            id="funds_trans",
                            options=[
                                {"label": x, "value": x}
                                for x in fundsportfolio.transactions()[
                                    "Fund Name"
                                ].unique()
                            ],
                            multi=True,
                            value=fundsportfolio.transactions()["Fund Name"].unique(),
                        ),
                    ]
                ),
            ]
        ),
        dbc.Row(
            dbc.Col(
                html.Div(id="funds_transaction_table"),
            )
        ),
    ],
    fluid=True,
)


#############################################################################
# Callbacks
#############################################################################


@app.callback(
    Output(component_id="funds_transaction_table", component_property="children"),
    [Input(component_id="funds_trans", component_property="value")],
)
def update_transaction_table(option_funds):
    print("#####################")
    print("# update transaction table option_funds: ", option_funds)
    pd_df = fundsportfolio.transactions()
    pd_df = pd_df.loc[pd_df["Fund Name"].isin(option_funds)]
    columns = []
    for col in pd_df.columns:
        col_fmt = {"name": col, "id": col}
        if col in ["Value", "Adj Value"]:
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
