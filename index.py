#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app import app

from apps import fii_dash, stocks_dash

from dash.dependencies import Input, Output

import dash_bootstrap_components as dbc

import dash_core_components as dcc

import dash_html_components as html


header = dbc.Row(
    dbc.Col(
        html.H1(
            "My personal investments tracker", className="text-center text-dark mb-4"
        ),
        width=12,
    )
)

navbar = dbc.Navbar(
    [
        dbc.NavLink("Home", href="/", active="exact"),
        dbc.NavLink("FII", href="/fii", active="exact"),
        dbc.NavLink("Stocks", href="/stocks", active="exact"),
    ],
    color="dark",
    className="justify-content-center nav-pills",
)

content = html.Div(id="page-content", children=[])

app.layout = html.Div(
    [
        dcc.Location(id="url"),
        header,
        navbar,
        content,
    ]
)


@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def render_page_content(pathname):
    if pathname == "/":
        return html.P("This is the content of the home page!")
    elif pathname == "/fii":
        return fii_dash.layout
    elif pathname == "/stocks":
        return stocks_dash.layout
    # If the user tries to reach a different page, return a 404 message
    return dbc.Jumbotron(
        [
            html.H1("404: Not found", className="text-danger"),
            html.Hr(),
            html.P("The pathname {} was not found".format(pathname)),
        ]
    )


if __name__ == "__main__":
    app.run_server(debug=True)

# vim: ts=4
