# -*- coding: utf-8 -*-
"""Test monthly_position method."""

import pytest
from io import StringIO
import datetime
from unittest.mock import patch, Mock
import pandas as pd
from portfolio import fii


def pd_df(Ticker=None):
    data_csv = StringIO(
        """
Date;Ticker;Operation;Quantity;Unit Price;Operation Cost;Adj Qtd;Adj Cost;Adj unit price
2020-03-10;AAA11;Compra;10;100;1000;10;1000;100,000000
2020-03-11;AAA11;Compra;10;200;2000;20;3000;150,000000
2020-05-10;AAA11;Compra;10;100;1000;30;4000;133,333333
2020-07-10;AAA11;Compra;10;100;1000;40;5000;125,000000
2020-07-10;AAA11;Compra;10;100;1000;50;6000;120,000000
2020-08-10;AAA11; Venda;-10;100;-1000;40;5000;125,000000
2020-08-10;BBB11;Compra;50;120;6000;50;6000;120,000000
2020-11-10;BBB11;Compra;20;110;2200;70;8200;117,142857
"""
    )
    df = pd.read_csv(
        data_csv,
        sep=";",
        encoding="UTF-8",
        parse_dates=["Date"],
        dayfirst=True,
        thousands=".",
        decimal=",",
    )
    return df


datetime_now = datetime.datetime(2021, 1, 1)

expeted_result = """\
           Ticker  Adj Qtd  Adj Cost  Adj unit price  year  month
Date                                                             
2020-03-31  AAA11       20      3000      150.000000  2020      3
2020-04-30  AAA11       20      3000      150.000000  2020      4
2020-05-31  AAA11       30      4000      133.333333  2020      5
2020-06-30  AAA11       30      4000      133.333333  2020      6
2020-07-31  AAA11       50      6000      120.000000  2020      7
2020-08-31  AAA11       40      5000      125.000000  2020      8
2020-09-30  AAA11       40      5000      125.000000  2020      9
2020-10-31  AAA11       40      5000      125.000000  2020     10
2020-11-30  AAA11       40      5000      125.000000  2020     11
2020-12-31  AAA11       40      5000      125.000000  2020     12
2021-01-31  AAA11       40      5000      125.000000  2021      1
2020-08-31  BBB11       50      6000      120.000000  2020      8
2020-09-30  BBB11       50      6000      120.000000  2020      9
2020-10-31  BBB11       50      6000      120.000000  2020     10
2020-11-30  BBB11       70      8200      117.142857  2020     11
2020-12-31  BBB11       70      8200      117.142857  2020     12
2021-01-31  BBB11       70      8200      117.142857  2021      1"""


@patch("datetime.datetime")
def test_monthly_position(mock_datetime):
    mock_datetime.now.return_value = datetime_now
    with patch.object(fii.FiiTransactions, "__init__", return_value=None):
        fiiportfolio = fii.FiiPortfolio(None)
        with patch.object(fiiportfolio.fiitransactions, "transactions", pd_df):
            x = fiiportfolio.monthly_position()
    assert x.to_string() == expeted_result


# vim: ts=4
