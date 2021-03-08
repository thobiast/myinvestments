# -*- coding: utf-8 -*-
"""FII dashboard layout."""


from app import app

from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc

import dash_core_components as dcc

import dash_html_components as html

import plotly.express as px

from portfolio.fii import FiiPortfolio


fiiportfolio = FiiPortfolio("fii_transactions.csv")


#############################################################################
# Cards
#############################################################################
def create_card(title, content):
    card = dbc.Card(
        dbc.CardBody(
            [
                html.H4(title, className="card-title"),
                html.P(content, className="card-text"),
            ]
        ),
        color="info",
        inverse=True,
    )
    return card


card1 = create_card(
    "Total amount invested", "R$ {:,.2f}".format(fiiportfolio.total_invest[0])
)
card2 = create_card("Current value", "R$ {:,.2f}".format(fiiportfolio.total_invest[1]))
card3 = create_card(
    "Last month dividend yield", "{:.3f} %".format(fiiportfolio.total_dividend_yield)
)
card4 = create_card(
    "All dividends received",
    "R$ {:,.2f}".format(fiiportfolio.calc_monthly_dividends()["Amount Received"].sum()),
)

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
fig_div_rcvd_yearly.update_layout(title_x=0.5, yaxis={"tickprefix": "R$ "})

fig_div_rcvd_monthly = px.bar(
    fiiportfolio.calc_monthly_dividends().sort_values(by=["Date"]),
    x="Date",
    y="Amount Received",
    color="Ticker",
    barmode="stack",
    title="Dividends Received Monthly",
)
fig_div_rcvd_monthly.update_layout(title_x=0.5, yaxis={"tickprefix": "R$ "})

fig_monthly_pos = px.line(
    fiiportfolio.monthly_position(),
    y="Adj Cost",
    color="Ticker",
    title="Monthly Position",
)
fig_monthly_pos.update_layout(
    title_x=0.5, yaxis_title="Money invested", yaxis={"tickprefix": "R$ "}
)

fig_portfolio_distribution = px.pie(
    fiiportfolio.current_position(),
    values="Adj Cost",
    names="Ticker",
    title="Porfolio Distribution",
)
fig_portfolio_distribution.update_layout(title_x=0.5)


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
                                    "R$ {:,.2f}".format(fiiportfolio.total_invest[0])
                                ),
                                dbc.ListGroupItem("Current Value:", color="secondary"),
                                dbc.ListGroupItem(
                                    "R$ {:,.2f}".format(fiiportfolio.total_invest[1])
                                ),
                                dbc.ListGroupItem(
                                    "All dividends received:", color="secondary"
                                ),
                                dbc.ListGroupItem(
                                    "R$ {:,.2f}".format(
                                        fiiportfolio.calc_monthly_dividends()[
                                            "Amount Received"
                                        ].sum()
                                    )
                                ),
                                dbc.ListGroupItem(
                                    "Last month dividend yield:", color="secondary"
                                ),
                                dbc.ListGroupItem(
                                    "{:.3f} %".format(fiiportfolio.total_dividend_yield)
                                ),
                            ],
                            horizontal=True,
                            className="mb-2",
                        ),
                    ],
                ),
            ],
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
                    width={"size": 9},
                ),
                dbc.Col(
                    [
                        dcc.Graph(
                            id="line1-fig2",
                            figure=fig_div_rcvd_yearly,
                        ),
                    ],
                    width={"size": 3},
                ),
            ],
        ),
        dbc.Row(
            [
                dbc.Col(
                    [dcc.Graph(id="line-fig2", figure=fig_monthly_pos)],
                ),
                dbc.Col(
                    [dcc.Graph(id="pie-fig1", figure=fig_portfolio_distribution)],
                ),
            ],
        ),
        dbc.Row([dbc.Col(html.H1(children="Current FII Position"), className="mb-4")]),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Table.from_dataframe(
                        fiiportfolio.current_position(),
                        striped=True,
                        bordered=True,
                        hover=True,
                        size="sm",
                    ),
                ),
            ],
        ),
        dbc.Row(
            [dbc.Col(html.H1(children="Monthly Detailed Dividends"), className="mb-4")]
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
    return dbc.Table.from_dataframe(
        pd_df,
        striped=True,
        bordered=True,
        hover=True,
        size="sm",
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
    return dbc.Table.from_dataframe(
        pd_df.sort_values(by=["Date", "Ticker"], ascending=[False, True]),
        striped=True,
        bordered=True,
        hover=True,
        size="sm",
    )


# vim: ts=4
