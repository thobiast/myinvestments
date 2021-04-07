# -*- coding: utf-8 -*-
"""Dashboard application."""


import dash

import dash_bootstrap_components as dbc

# https://hackerthemes.com/bootstrap-cheatsheet
# https://www.bootstrapcdn.com/bootswatch/
app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
    ],
)
app.title = "My investments"
server = app.server

# vim: ts=4
