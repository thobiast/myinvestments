# -*- coding: utf-8 -*-
"""Stocks Tracker."""

import os

import pandas as pd

from .portutils import UnitsTransactions, stocks_quote


# Default stocks portfolio csv file
# It is used if transaction file is not set
# on environment variable STOCKS_TRANSACTIONS
CSV_FILE = "example_transactions/stocks_transactions.csv"


class StocksPortfolio:
    """Class to handle the Stocks portfolio."""

    def __init__(self, filename=None):
        """Initialize stocks porfolio class."""
        self.filename = (
            filename if filename else os.getenv("STOCKS_TRANSACTIONS", CSV_FILE)
        )
        print("Stocks file: ", self.filename)
        self.stockstransactions = UnitsTransactions(self.filename)

    def current_position(self, ticker=None):
        """
        Return dataframe with current tickers position.

        Parameters:
            Ticker    (str): Return only for specific ticker.
                             Default: all
        """
        position_df = (
            self.stockstransactions.transactions(ticker)
            .groupby("Ticker")
            .tail(1)
            .copy()
        )

        # Filter out historical tickers, ie, ticker with current position is zero units
        position_df = position_df.loc[position_df["Adj Qtd"] != 0]

        # Add current quote and pct return
        position_df["Current Quote"] = position_df.apply(
            lambda x: stocks_quote(x["Ticker"]).iloc[0][0], axis=1
        )
        position_df["Current Value"] = (
            position_df["Current Quote"] * position_df["Adj Qtd"]
        )
        position_df["Gain/Loss Pct"] = (
            (position_df["Current Quote"] / position_df["Adj unit price"]) - 1
        ) * 100

        return position_df.drop(
            ["Operation", "Date", "Quantity", "Unit Price", "Operation Cost"],
            axis="columns",
        )

    def get_historical_prices(self):
        """Return dataframe with historical position and price."""
        tickers = self.current_position()["Ticker"].unique().tolist()

        result_df = pd.DataFrame()

        for ticker in tickers:
            # Get date there is the first transaction for ticker
            start_date = (
                self.stockstransactions.transactions(ticker)
                .head(1)["Date"]
                .iloc[0]
                .to_pydatetime()
            )
            # Get historical quote for ticker
            quote_df = stocks_quote(ticker, start_date.date())

            # Get ticker transactions
            pd_df = (
                self.stockstransactions.transactions(ticker)
                .set_index("Date")
                .drop(["Operation", "Quantity", "Unit Price"], axis="columns")
            )

            # Concat dataframes with transactions and quotes for ticker
            result_tmp_df = pd.concat([pd_df, quote_df], axis="columns")
            result_tmp_df.fillna(method="ffill", inplace=True)
            result_tmp_df.reset_index("Date", inplace=True)

            # Concat result_tmp dataframe with the one the has final result
            result_df = pd.concat([result_df, result_tmp_df])

        return result_df

    @property
    def total_invest(self):
        """Return total amount invested and the current holdings value."""
        return (
            self.current_position()["Adj Cost"].sum(),
            self.current_position()["Current Value"].sum(),
        )

    @property
    def total_return(self):
        """Return current performancei pct."""
        return_pct = ((self.total_invest[1] / self.total_invest[0]) - 1) * 100
        return return_pct


# vim: ts=4
