# -*- coding: utf-8 -*-
"""Portfolio tracker utils functions."""


import datetime
import functools
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

import pandas as pd

import pandas_datareader as pdr

import requests_cache


CACHE_EXPIRE_DAYS = 1
requests_cache.install_cache(
    cache_name="portutils",
    backend="sqlite",
    expire_after=datetime.timedelta(days=CACHE_EXPIRE_DAYS),
)


# Num process to parallel execution of some functions
NUM_PROCESS = os.cpu_count() - 1


@functools.lru_cache()
def stocks_quote(ticker, exchange, start_date=None, end_date=None):
    """
    Return dataframe with ticker price(s).

    Parameters:
        ticker               (str): ticker
        exchange             (str): stock exchange
        start_date  (str/datetime): start date to search quotes
                                    default: today
        end_date    (str/datetime): end date to search quoted
                                    default: today
    """
    print("Getting prices for ticker ", ticker, os.getpid())
    start = start_date if start_date else datetime.datetime.today().date()
    end = end_date if end_date else datetime.datetime.today().date()

    ticker = "{}.SA".format(ticker) if exchange == "B3" else ticker

    try:
        quote_df = pdr.DataReader(ticker, "yahoo", start, end)
    except KeyError:
        print("Error: no price for today. Trying days ago")
        days_ago = end - datetime.timedelta(days=7)
        quote_df = pdr.DataReader(ticker, "yahoo", days_ago, end)

    return quote_df[["Close"]]


class UnitsTransactions:
    """Class to handle the Units transactions (csv file)."""

    def __init__(self, filename):
        """
        Initialize units transactions class.

        Read csv file with following fields:
            Date;Broker;Stock Exchange;Ticker;Operation;Quantity;Unit Price
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
        self.current_position_df = pd.DataFrame()

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

    @staticmethod
    def _add_current_quote_to_df(pd_df):
        """
        Add current quote to dataframe.

        Return dataframe with new column
        """
        print("add_current_quote_to_df: ", os.getpid())

        # Add current quote
        pd_df["Current Quote"] = pd_df.apply(
            lambda x: stocks_quote(x["Ticker"], x["Stock Exchange"]).iloc[0][0], axis=1
        )

        return pd_df

    def current_position(self, refresh=False):
        """
        Return dataframe with current tickers position.

        Parameters:
            refresh   (True/False): Force data refresh

        Return Data Frame
        """
        if not self.current_position_df.empty and not refresh:
            return self.current_position_df

        position_df = self.transactions().groupby("Ticker").tail(1).copy()

        # Filter out historical tickers, ie, ticker with current position is zero units
        position_df = position_df.loc[position_df["Adj Qtd"] != 0]

        # Parallel execution to add new column with current quote
        global NUM_PROCESS
        num_p_exec = len(position_df) if len(position_df) < NUM_PROCESS else NUM_PROCESS
        df_chunks = np.array_split(position_df, num_p_exec)
        with ProcessPoolExecutor(max_workers=num_p_exec) as executors:
            result = executors.map(self._add_current_quote_to_df, df_chunks)
        position_df = pd.concat(result)

        position_df["Current Value"] = (
            position_df["Current Quote"] * position_df["Adj Qtd"]
        )
        position_df["Gain/Loss Pct"] = (
            (position_df["Current Quote"] / position_df["Adj unit price"]) - 1
        ) * 100

        self.current_position_df = position_df.drop(
            ["Operation", "Date", "Quantity", "Unit Price", "Operation Cost"],
            axis="columns",
        )
        return self.current_position_df

    def get_historical_position_prices_for_ticker(self, ticker):
        """Return dataframe with historical position and price for a ticker."""
        # Get date there is the first transaction for ticker
        start_date = self.transactions(ticker).head(1)["Date"].iloc[0].to_pydatetime()

        # Get stock exchange
        exchange = self.transactions(ticker).head(1)["Stock Exchange"].iloc[0]
        # Get historical quote for ticker.
        # Start day is the first time a ticker was bought
        # End day is today
        quote_df = stocks_quote(ticker, exchange, start_date.date())

        # Get ticker transactions
        pd_df = self.transactions(ticker).drop(
            ["Operation", "Quantity", "Unit Price"], axis="columns"
        )

        # Convert datetime to date
        pd_df["Date"] = pd.to_datetime(pd_df["Date"]).dt.date
        pd_df.drop_duplicates("Date", keep="last", inplace=True)
        pd_df.set_index("Date", inplace=True)

        # Concat dataframes with transactions and quotes for ticker
        result_tmp_df = pd.concat([pd_df, quote_df], axis="columns")
        result_tmp_df.fillna(method="ffill", inplace=True)
        result_tmp_df.reset_index("Date", inplace=True)

        result_tmp_df["Position updated"] = (
            result_tmp_df["Adj Qtd"] * result_tmp_df["Close"]
        )
        return result_tmp_df

    def get_historical_position_prices(self, ticker=None):
        """
        Return dataframe with historical position and price.

        Concat dataframe with historical daily tickers prices with
        the ticker position at that day.
        """
        print("### get_historical_position_prices")
        # Get list with all tickers
        tickers = self.current_position(ticker)["Ticker"].unique().tolist()

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executors:
            result = executors.map(
                self.get_historical_position_prices_for_ticker,
                tickers,
            )
        result_df = pd.concat(result)

        return result_df.dropna()

    def money_invested_monthly(self):
        """Return dataframe with amount of money invested monthly."""
        pd_df = self.transactions()
        return (
            pd_df.groupby(pd_df["Date"].dt.strftime("%Y-%m"))[["Operation Cost"]]
            .sum()
            .reset_index("Date")
        )


class Singleton(type):
    """Create singleton class."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Check if there is instance before initialize."""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


# vim: ts=4
