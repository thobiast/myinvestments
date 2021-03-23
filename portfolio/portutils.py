# -*- coding: utf-8 -*-
"""Portfolio tracker utils functions."""


import datetime
import functools

import pandas as pd

import pandas_datareader as pdr

import requests_cache


CACHE_EXPIRE_DAYS = 1
requests_cache.install_cache(
    cache_name="portutils",
    backend="sqlite",
    expire_after=datetime.timedelta(days=CACHE_EXPIRE_DAYS),
)


@functools.lru_cache()
def stocks_quote(ticker, start_date=None, end_date=None):
    """
    Return dataframe with ticker price(s).

    Parameters:
        ticker      (str): ticker
        start_date  (str/datetime): start date to search quotes
                                    default: today
        end_date    (str/datetime): end date to search quoted
                                    default: today
    """
    print("Getting current price for ticker ", ticker)
    start = start_date if start_date else datetime.datetime.today().date()
    end = end_date if end_date else datetime.datetime.today().date()

    try:
        quote_df = pdr.DataReader("{}.SA".format(ticker), "yahoo", start, end)
    except KeyError:
        print("Error: no price for today. Trying days ago")
        days_ago = end - datetime.timedelta(days=7)
        quote_df = pdr.DataReader("{}.SA".format(ticker), "yahoo", days_ago, end)

    return quote_df[["Close"]]


class UnitsTransactions:
    """Class to handle the Units transactions (csv file)."""

    def __init__(self, filename):
        """
        Initialize units transactions class.

        Read csv file with following fields:
            Date;Ticker;Operation;Quantity;Unit Price
        """
        if filename.endswith((".xls", ".xlsx")):
            self.pd_df = pd.read_excel(
                filename,
                parse_dates=["Date"],
                thousands=".",
            )
        else:
            self.pd_df = pd.read_csv(
                filename,
                sep=";",
                encoding="UTF-8",
                parse_dates=["Date"],
                dayfirst=True,
                thousands=".",
                decimal=",",
            )

        self.pd_df.sort_values(
            ["Ticker", "Date", "Operation"], ascending=[True, True, True], inplace=True
        )
        self.pd_df["Quantity"] = self._convert_qty_unit_to_negative()
        self.pd_df["Operation Cost"] = self._add_operation_cost()
        self.pd_df["Adj Qtd"] = self._add_adjusted_quantity_per_ticker()
        self._add_adjusted_total_invest_per_ticker()
        self.pd_df["Adj unit price"] = self._add_adjusted_price_per_ticker()

    def _convert_qty_unit_to_negative(self):
        """Convert the number of quantity units to negative for sells operations."""
        return self.pd_df.apply(
            lambda x: -x["Quantity"] if x["Operation"] == "Venda" else x["Quantity"],
            axis="columns",
        )

    def _add_operation_cost(self):
        """Return the total cost for each operation."""
        return self.pd_df["Quantity"] * self.pd_df["Unit Price"]

    def _add_adjusted_quantity_per_ticker(self):
        """Return the adjusted quantity for each ticker (cumulative sum)."""
        return self.pd_df.groupby("Ticker")["Quantity"].cumsum()

    def _add_adjusted_total_invest_per_ticker(self):
        """
        Add to dataframe the adjusted cost for each ticker operation.

        It calculate the cumulative sum for unit quantities.
        """
        self.pd_df["reset"] = (
            self.pd_df.groupby("Ticker")["Adj Qtd"].shift(1) == 0
        ).cumsum()
        self.pd_df["Adj Cost"] = self.pd_df.groupby(["Ticker", "reset"])[
            "Operation Cost"
        ].cumsum()
        self.pd_df.loc[self.pd_df["Adj Qtd"] == 0, "Adj Cost"] = 0
        self.pd_df.drop(["reset"], axis="columns", inplace=True)

    def _add_adjusted_price_per_ticker(self):
        """Return the adjusted unit price for each ticker on operation."""
        return self.pd_df.apply(
            lambda x: 0 if x["Adj Qtd"] == 0 else x["Adj Cost"] / x["Adj Qtd"],
            axis="columns",
        )

    def transactions(self, ticker=None):
        """
        Return dataframe with all transactions.

        Parameters:
            Ticker    (str): Return only operation for specific ticker.
                             Default: all
        """
        if ticker:
            return self.pd_df[self.pd_df["Ticker"] == ticker]
        else:
            return self.pd_df


# vim: ts=4
