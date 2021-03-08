# -*- coding: utf-8 -*-
"""Test current position method."""

import pytest
from io import StringIO
from unittest.mock import patch, Mock
import pandas as pd
from portfolio import fii


def pd_df(Ticker=None):
    data_csv = StringIO(
        """
Date;Ticker;Operation;Quantity;Unit Price;Operation Cost;Adj Qtd;Adj Cost;Adj unit price
2020-03-10;AAA11;Compra;10;100;1000;10;1000;100.000000
2020-03-11;AAA11;Compra;10;200;2000;20;3000;150.000000
2020-05-10;AAA11;Compra;10;100;1000;30;4000;133.333333
2020-07-10;AAA11;Compra;10;100;1000;40;5000;125.000000
2020-07-10;AAA11;Compra;10;100;1000;50;6000;120.000000
2020-08-10;AAA11; Venda;-10;100;-1000;40;5000;125.000000
2020-03-10;BBB11;Compra;50;120;6000;50;6000;120.000000
2020-04-10;BBB11;Compra;20;110;2200;70;8200;117.142857
"""
    )
    df = pd.read_csv(
        data_csv,
        sep=";",
        encoding="UTF-8",
        parse_dates=True,
    )
    return df


def mock_fii_quote(ticker=None, start_date=None, end_date=None):
    return pd.DataFrame(data={"Close": 150}, index=["2020/01/01"])


def test_current_position():
    expected_result = """\
  Ticker  Adj Qtd  Adj Cost  Adj unit price  Current Quote  Current Value  Gain/Loss Pct
5  AAA11       40      5000      125.000000            150           6000      20.000000
7  BBB11       70      8200      117.142857            150          10500      28.048781"""
    with patch.object(fii.FiiTransactions, "__init__", return_value=None):
        fiiportfolio = fii.FiiPortfolio(None)
        with patch.object(fiiportfolio.fiitransactions, "transactions", pd_df):
            with patch.object(fii, "fii_quote", mock_fii_quote):
                x = fiiportfolio.current_position()
    assert x.to_string() == expected_result


# vim: ts=4
