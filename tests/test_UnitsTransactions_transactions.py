# -*- coding: utf-8 -*-
"""Test transactions  method."""

import pytest
from unittest.mock import patch
from portfolio import portutils


# Basic test
file_csv_0 = """
Date;Ticker;Operation;Quantity;Unit Price
26/03/2020;AAA11;Compra;10;97,80
"""
result_0 = """\
        Date Ticker Operation  Quantity  Unit Price  Operation Cost  Adj Qtd  Adj Cost  Adj unit price
0 2020-03-26  AAA11    Compra        10        97.8           978.0       10     978.0            97.8"""

# Test cumulative sum (Adjusted values)
file_csv_1 = """
Date;Ticker;Operation;Quantity;Unit Price
10/03/2020;BBB11;Compra;50;120
10/04/2020;BBB11;Compra;20;110
10/03/2020;AAA11;Compra;10;100
11/03/2020;AAA11;Compra;10;200
10/05/2020;AAA11;Compra;10;100
10/07/2020;AAA11;Compra;10;100
10/07/2020;AAA11;Compra;10;100
10/08/2020;AAA11;Venda;10;100
"""
result_1 = """\
        Date Ticker Operation  Quantity  Unit Price  Operation Cost  Adj Qtd  Adj Cost  Adj unit price
2 2020-03-10  AAA11    Compra        10         100            1000       10      1000      100.000000
3 2020-03-11  AAA11    Compra        10         200            2000       20      3000      150.000000
4 2020-05-10  AAA11    Compra        10         100            1000       30      4000      133.333333
5 2020-07-10  AAA11    Compra        10         100            1000       40      5000      125.000000
6 2020-07-10  AAA11    Compra        10         100            1000       50      6000      120.000000
7 2020-08-10  AAA11     Venda       -10         100           -1000       40      5000      125.000000
0 2020-03-10  BBB11    Compra        50         120            6000       50      6000      120.000000
1 2020-04-10  BBB11    Compra        20         110            2200       70      8200      117.142857"""

# Test if it sells all position the adjusted values also get reseted, i.e,
# it does count previous valores with next buy
file_csv_2 = """
Date;Ticker;Operation;Quantity;Unit Price
10/03/2020;BBB11;Compra;50;122
10/03/2020;AAA11;Compra;10;100
11/03/2020;AAA11;Compra;10;200
10/05/2020;AAA11;Venda;20;100
10/07/2020;AAA11;Compra;10;100
10/08/2020;AAA11;Compra;10;200
"""
result_2 = """\
        Date Ticker Operation  Quantity  Unit Price  Operation Cost  Adj Qtd  Adj Cost  Adj unit price
1 2020-03-10  AAA11    Compra        10         100            1000       10      1000           100.0
2 2020-03-11  AAA11    Compra        10         200            2000       20      3000           150.0
3 2020-05-10  AAA11     Venda       -20         100           -2000        0         0             0.0
4 2020-07-10  AAA11    Compra        10         100            1000       10      1000           100.0
5 2020-08-10  AAA11    Compra        10         200            2000       20      3000           150.0
0 2020-03-10  BBB11    Compra        50         122            6100       50      6100           122.0"""


@pytest.mark.parametrize(
    "filename, csv_file, result",
    [
        ("file0.csv", file_csv_0, result_0),
        ("file1.csv", file_csv_1, result_1),
        ("file2.csv", file_csv_2, result_2),
    ],
)
def test_transactions(filename, csv_file, result, tmp_path):
    p = tmp_path / filename
    p.write_text(csv_file)
    unittransaction = portutils.UnitsTransactions(str(p))
    pd_df = unittransaction.transactions()
    assert pd_df.to_string() == result


# vim: ts=4
