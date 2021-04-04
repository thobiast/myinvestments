# -*- coding: utf-8 -*-
"""Home dashboard layout."""

import locale

from apps import utils_dash

import dash_bootstrap_components as dbc

import dash_core_components as dcc

import pandas as pd

import plotly.express as px
import plotly.graph_objects as go

from portfolio.fii import FiiPortfolio
from portfolio.funds import FundsPortfolio
from portfolio.stocks import StocksPortfolio

print("locale: ", locale.setlocale(locale.LC_ALL, utils_dash.my_locale))

stocksportfolio = StocksPortfolio()
fiiportfolio = FiiPortfolio()
fundsportfolio = FundsPortfolio()

#############################################################################
# Figures
#############################################################################

fig_class_distribution_labels = ["Stocks", "FIIs", "Funds"]
fig_class_distribution_values = []
fig_class_distribution_values.append(stocksportfolio.total_invest()[1])
fig_class_distribution_values.append(fiiportfolio.total_invest[1])
fig_class_distribution_values.append(fundsportfolio.total_invest[1])

fig_class_distribution = go.Figure(
    data=[
        go.Pie(
            labels=fig_class_distribution_labels, values=fig_class_distribution_values
        )
    ]
)
fig_class_distribution.update_layout(title="Porfolio Class Distribution", title_x=0.5)


df_fii_money_monthly = fiiportfolio.fiitransactions.money_invested_monthly()
df_fii_money_monthly["Class"] = "FII"
df_fun_money_monthly = fundsportfolio.money_invested_monthly()
df_fun_money_monthly.rename(columns={"Value": "Operation Cost"}, inplace=True)
df_fun_money_monthly["Class"] = "Funds"
df_sto_money_monthly = stocksportfolio.stockstransactions.money_invested_monthly()
df_sto_money_monthly["Class"] = "Stocks"
fig_money_inv_monthly = px.bar(
    pd.concat([df_fii_money_monthly, df_fun_money_monthly, df_sto_money_monthly]),
    x="Date",
    y="Operation Cost",
    labels={"Operation Cost": "Amount Invested", "Date": "Month"},
    color="Class",
    title="Money Invested Monthly",
)
fig_money_inv_monthly.update_layout(
    title_x=0.5, yaxis={"tickprefix": utils_dash.graph_money_prefix}
)
fig_money_inv_monthly.update_xaxes(rangeslider_visible=True)
fig_money_inv_monthly.update_layout(
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
# layout
#############################################################################

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Graph(
                            id="fig_class_distribution_id",
                            figure=fig_class_distribution,
                        )
                    ],
                ),
                dbc.Col(
                    [
                        dcc.Graph(
                            id="fig_money_inv_monthly_id",
                            figure=fig_money_inv_monthly,
                        )
                    ],
                ),
            ]
        ),
    ],
    fluid=True,
)

# vim: ts=4
