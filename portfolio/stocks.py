# -*- coding: utf-8 -*-
"""Stocks Tracker."""

import datetime
import os

import pandas as pd

import pandas_datareader as pdr

import requests_cache

from .portutils import UnitsTransactions, stocks_quote


# Cache for dividends
CACHE_EXPIRE_DAYS = 7
requests_cache.install_cache(
    cache_name="stockdiv",
    backend="sqlite",
    expire_after=datetime.timedelta(days=CACHE_EXPIRE_DAYS),
)

# Default stocks portfolio csv file
# It is used if transaction file is not set
# on environment variable STOCKS_TRANSACTIONS
CSV_FILE = "example_transactions/stocks_transactions.csv"


class StocksDividends:
    """Class to handle dividends."""

    def __init__(self):
        """Initialize stocks dividends class."""
        self.dividends = {}

    def download_dividends(self, ticker, exchange, start_date=None, end_date=None):
        """
        Download all dividends paid out for a ticker.

        Parameters:
            ticker    (str): Stock ticker
            exchange  (str): Stock exchange
            start    (date): start date to search
            end      (date): date to stop search
        """
        print("Getting dividends: ", ticker, start_date)
        start = start_date if start_date else datetime.datetime.today().date()
        end = end_date if end_date else datetime.datetime.today().date()

        ticker_ya = "{}.SA".format(ticker) if exchange == "B3" else ticker
        try:
            self.dividends[ticker] = pdr.DataReader(
                ticker_ya, "yahoo-dividends", start, end
            )
        except (KeyError, pdr._utils.RemoteDataError):
            self.dividends[ticker] = pd.DataFrame()

    def get_ticker_dividends(self, ticker, exchange, start_date=None, end_date=None):
        """
        Return DataFrame with dividends paid out for a ticker.

        Parameters:
            ticker    (str): Stock ticker
            exchange  (str): Stock exchange
            start    (date): start date to search
            end      (date): date to stop search

        Return:  DataFrame
        """
        if ticker not in self.dividends:
            self.download_dividends(ticker, exchange, start_date, end_date)

        return self.dividends[ticker]


class StocksPortfolio:
    """Class to handle the Stocks portfolio."""

    def __init__(self, filename=None):
        """Initialize stocks porfolio class."""
        self.filename = (
            filename if filename else os.getenv("STOCKS_TRANSACTIONS", CSV_FILE)
        )
        print("Stocks file: ", self.filename)
        self.stockstransactions = UnitsTransactions(self.filename)
        self.stocksdividends = StocksDividends()

    def current_position(self, ticker=None):
        """
        Return dataframe with current tickers position.

        Parameters:
            Ticker    (str): Return only for specific ticker.
                             Default: all
        """
        return self.stockstransactions.current_position(ticker)

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
            # Get stock exchange
            exchange = (
                self.stockstransactions.transactions(ticker)
                .head(1)["Stock Exchange"]
                .iloc[0]
            )
            # Get historical quote for ticker
            quote_df = stocks_quote(ticker, exchange, start_date.date())

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

            result_tmp_df["Position updated"] = (
                result_tmp_df["Adj Qtd"] * result_tmp_df["Close"]
            )
            # Concat result_tmp dataframe with the one the has final result
            result_df = pd.concat([result_df, result_tmp_df])

        return result_df.dropna()

    def get_div_position(self, ticker, date):
        """
        Return the last stock Adj Qtd of a stock position before a date.

        Parameters:
            ticker   (str): ticker
            date     (date): date to filter position
        """
        ticker_df = self.stockstransactions.transactions(ticker).copy()
        qtd = ticker_df[ticker_df["Date"] <= date]["Adj Qtd"].tail(1)
        qtd = None if qtd.empty else qtd.values[0]
        return qtd

    def get_dividends(self):
        """Return dataframe with dividends paid out."""
        result_df = pd.DataFrame()

        # Get the ticker and first date it was bought
        # It is used to query dividends only after the first time it bought the ticker,
        # so it can not query all dividends history of a ticker
        first_day_df = (
            self.stockstransactions.transactions()
            .groupby("Ticker")[["Date", "Ticker", "Stock Exchange"]]
            .head(1)
        )

        for _, row in first_day_df.iterrows():
            # Get dividends for a ticker. Dividends paid out after the first transaction
            div_df = self.stocksdividends.get_ticker_dividends(
                row.Ticker, row["Stock Exchange"], start_date=row.Date
            ).copy()
            if div_df.empty:
                print("No dividends for ticker: ", row.Ticker)
            else:
                div_df.index.name = "date"
                div_df["Ticker"] = row.Ticker
                div_df.reset_index(inplace=True)
                div_df["Month"] = div_df["date"].dt.strftime("%Y-%m")
                div_df["Year"] = div_df["date"].dt.strftime("%Y")
                # For each dividend paid, check if it had a position at that date.
                div_df["Units"] = div_df.apply(
                    lambda x: self.get_div_position(row.Ticker, x["date"]), axis=1
                )
                # Remove rows with zero units (if we sell all position)
                div_df = div_df.loc[div_df["Units"] != 0]
                div_df["Dividends"] = div_df["Units"] * div_df["value"]
                result_df = pd.concat([result_df, div_df])

        return result_df.sort_values(by="date")

    def dividends_received(self, period="Year"):
        """
        Return total dividend received by ticker and year or month.

        Parameters:
            Period      (year/month): default year
        """
        pd_df = self.get_dividends()
        return pd_df.groupby([period, "Ticker"]).sum().reset_index()

    def total_invest(self, by_col=None):
        """
        Return total amount invested and the current holdings value.

        Parameters:
            by_col   (str): if it should group (aggregate) the result by
                            a column. Example: Broker
                            default: no aggregation

        """
        if by_col:
            pd_df = self.current_position().groupby(by_col)
        else:
            pd_df = self.current_position()

        return (pd_df["Adj Cost"].sum(), pd_df["Current Value"].sum())

    @property
    def total_return(self):
        """Return current performance pct."""
        return_pct = ((self.total_invest()[1] / self.total_invest()[0]) - 1) * 100
        return return_pct


# vim: ts=4
