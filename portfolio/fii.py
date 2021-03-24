# -*- coding: utf-8 -*-
"""Tracker REITs (Real Estate Investment Trust) investments."""


import datetime
import os

import pandas as pd

import requests

import requests_cache

from .portutils import UnitsTransactions, stocks_quote

# Cache for dividends
CACHE_EXPIRE_DAYS = 15
requests_cache.install_cache(
    cache_name="fiidiv",
    backend="sqlite",
    expire_after=datetime.timedelta(days=CACHE_EXPIRE_DAYS),
)

# Default fii portfolio csv file
# It is used if transaction file is not set
# on environment variable FII_TRANSACTIONS
CSV_FILE = "example_transactions/fii_transactions.csv"


class FiiDividends:
    """Class to handle dividends."""

    URL = "https://mfinance.com.br/api/v1/fiis/dividends"

    def __init__(self):
        """Initialize fii dividends class."""
        self.dividends = {}

    def load_dividends(self, ticker):
        """
        Download all dividends paid out for a ticker.

        Parameters:
            ticker   (str): FII ticker
        """
        ticker_url = "{}/{}".format(self.URL, ticker)
        print("Getting dividends: ", ticker_url)

        # To not use request cache to get "current" price,
        # comment next line and uncomment the other
        df_tmp = pd.read_json(requests.get(ticker_url).content)
        # df_tmp = pd.read_json(ticker_url)

        df_dividends = pd.json_normalize(df_tmp.dividends)
        df_dividends["payDate"] = pd.to_datetime(df_dividends["payDate"])
        df_dividends["declaredDate"] = pd.to_datetime(df_dividends["declaredDate"])
        self.dividends[ticker] = df_dividends

    def get_month(self, ticker, year, month):
        """
        Return dividends paid out in a month for a ticker and the pay date.

        Parameters:
            ticker   (str): Fii ticker
            year     (int): year (YYYY)
            month    (int): month

        Return:  (dividend_value, pay_date)
        """
        if ticker not in self.dividends:
            self.load_dividends(ticker)

        m_filter = self.dividends[ticker]["declaredDate"].dt.month == month
        y_filter = self.dividends[ticker]["declaredDate"].dt.year == year
        div_value = self.dividends[ticker][y_filter & m_filter].value
        pay_date = self.dividends[ticker][y_filter & m_filter].payDate
        if div_value.empty:
            return (None, None)
        else:
            return (div_value.iloc[0], pay_date.iloc[0].strftime("%Y-%m-%d"))


class Singleton(type):
    """Create singleton class."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Check if there is instance before initialize."""
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class FiiPortfolio(metaclass=Singleton):
    """Class to handle the FII portfolio."""

    def __init__(self, filename=None):
        """Initialize fii porfolio class."""
        self.filename = (
            filename if filename else os.getenv("FII_TRANSACTIONS", CSV_FILE)
        )
        print("Fii file: ", self.filename)
        self.fiitransactions = UnitsTransactions(self.filename)
        self.fiidiv = FiiDividends()

    def current_position(self, ticker=None):
        """
        Return dataframe with current tickers position.

        Parameters:
            Ticker    (str): Return only for specific ticker.
                             Default: all
        """
        return self.fiitransactions.current_position(ticker)

    def get_historical_position_prices(self, ticker=None):
        """
        Return dataframe with historical position and price.

        Concat dataframe with historical daily tickers prices with
        the ticker position at that day.
        """
        return self.fiitransactions.get_historical_position_prices(ticker)

    def monthly_position(self, ticker=None):
        """Return a dataframe with monthly position (holdings)."""
        pd_df_tmp = self.fiitransactions.transactions(ticker).copy()

        # Drop unnecessary columns
        pd_df_tmp = pd_df_tmp.drop(
            ["Quantity", "Operation", "Unit Price", "Operation Cost"], axis="columns"
        )

        # Since it may not have transaction in the current month, it add
        # a row with the repeating the last position with current date time.
        today_pos = pd_df_tmp.sort_values(by="Date").groupby("Ticker").tail(1)
        today_pos["Date"] = datetime.datetime.now()
        # Join all "transaction" with the fake one, so it can use resample
        # to generate monthly position
        monthly_pos = pd.concat([pd_df_tmp, today_pos], ignore_index=True)
        # If there are more than 1 operation on same day for a ticker,
        # add some 'ms' to datetime to avoid duplicated index
        monthly_pos["Date"] = monthly_pos["Date"] + pd.to_timedelta(
            monthly_pos.groupby("Date").cumcount(), unit="ms"
        )
        monthly_pos.set_index("Date", inplace=True)
        monthly_pos = (
            monthly_pos.groupby("Ticker")
            .resample("M")
            .fillna("pad")
            .reset_index(level="Ticker", drop=True)
        )

        monthly_pos["year"] = monthly_pos.index.year
        monthly_pos["month"] = monthly_pos.index.month

        return monthly_pos

    def calc_monthly_dividends(self, sort_date_ascending=True):
        """
        Return a dataframe with dividends paid out monthly per ticker.

        Parameters:
            sort_date_ascending  (True/False): Return dataframe with Date column
                                               sorted ascending or descending
                                               default:  True - ascending
        """
        pd_df = self.monthly_position().copy()
        # Add dividends monthly
        pd_df["Monthly Dividends"] = pd_df.apply(
            lambda x: self.fiidiv.get_month(x["Ticker"], x["year"], x["month"])[0],
            axis=1,
        )
        # Add dividend pay date
        pd_df["Pay Date"] = pd_df.apply(
            lambda x: self.fiidiv.get_month(x["Ticker"], x["year"], x["month"])[1],
            axis=1,
        )
        # Calculate money received
        pd_df["Amount Received"] = pd_df["Monthly Dividends"] * pd_df["Adj Qtd"]
        # Get current ticker price
        pd_df["Current Quote"] = pd_df.apply(
            lambda x: stocks_quote(x["Ticker"], x["Stock Exchange"]).tail(1).iloc[0][0],
            axis=1,
        )
        # Calculate dividend yield for price it paid for ticker and for
        # current ticker price
        pd_df["Dividend Yield on Cost"] = (
            pd_df["Monthly Dividends"] / pd_df["Adj unit price"]
        ) * 100
        pd_df["Dividend Yield"] = (
            pd_df["Monthly Dividends"] / pd_df["Current Quote"]
        ) * 100

        pd_df.reset_index("Date", inplace=True)
        pd_df.sort_values(
            by=["Date", "Ticker"], ascending=[sort_date_ascending, True], inplace=True
        ),
        pd_df["Date"] = pd_df["Date"].apply(lambda x: x.strftime("%Y-%b"))
        pd_df["Pay Month"] = (
            pd.to_datetime(pd_df["Pay Date"])
            .dropna()
            .apply(lambda x: x.strftime("%Y-%b"))
        )

        return pd_df.loc[pd_df["Monthly Dividends"].notna()]

    @property
    def total_invest_monthly(self):
        """Return dataframe with total position monthly."""
        pd_df = self.monthly_position()
        pd_df = (
            pd_df.resample("M")
            .sum()
            .drop(["Adj Qtd", "Adj unit price"], axis="columns")
        )
        return pd_df

    @property
    def total_invest(self):
        """Return total amount invested and the current holdings value."""
        return (
            self.current_position()["Adj Cost"].sum(),
            self.current_position()["Current Value"].sum(),
        )

    @property
    def total_dividend_yield(self):
        """Return portfolio dividend yield for last month."""
        pd_df = self.calc_monthly_dividends()
        units_cost = pd_df.groupby("Ticker").tail(1)["Current Quote"].sum()
        dividends = pd_df.groupby("Ticker").tail(1)["Amount Received"].sum()
        div_yield = (dividends / units_cost) * 100
        return div_yield

    def total_dividend_received(self, period="year"):
        """
        Return total dividend received by ticker and year or month.

        Parameters:
            period      (year/month): default year
        """
        pd_df = self.calc_monthly_dividends()
        return pd_df.groupby([period, "Ticker"]).sum().reset_index()


# vim: ts=4
