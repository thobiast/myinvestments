# -*- coding: utf-8 -*-
"""Helper functions to dashboards."""

from dash_table import FormatTemplate
from dash_table.Format import Format, Group, Scheme, Symbol

# dash_table columns format
money = Format(
    scheme=Scheme.fixed,
    precision=2,
    group=Group.yes,
    groups=3,
    group_delimiter=".",
    decimal_delimiter=",",
    symbol=Symbol.yes,
    symbol_prefix="R$",
)
percentage = FormatTemplate.Format(
    decimal_delimiter=",",
    precision=2,
    scheme=Scheme.fixed,
    symbol=Symbol.yes,
    symbol_suffix="%",
)

# plotly graphs
graph_money_prefix = "R$ "

# Set locale. It is used to properly set number and currency.
# Examples:
# en_US.UTF-8
# pt_BR.utf8
my_locale = "pt_BR.utf8"
