#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tracker REITs (Real Estate Investment Trust) investments."""


import datetime
import functools

import pandas as pd

import pandas_datareader as pdr

import requests

import requests_cache


CACHE_EXPIRE_DAYS = 15
requests_cache.install_cache(
    cache_name="fiidiv",
    backend="sqlite",
    expire_after=datetime.timedelta(days=CACHE_EXPIRE_DAYS),
)


@functools.lru_cache
def fii_quote(ticker, start_date=None, end_date=None):
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

    return quote_df[["Close"]].tail(1)


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


class FiiTransactions:
    """Class to handle the fii transaction (csv file)."""

    def __init__(self, filename):
        """
        Initialize fii class.

        Read csv file with following fields:
            Date;Ticker;Operation;Quantity;Unit Price
        """
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


class FiiPortfolio:
    """Class to handle the FII portfolio."""

    def __init__(self, filename):
        """Initialize fii porfolio class."""
        self.fiitransactions = FiiTransactions(filename)
        self.fiidiv = FiiDividends()

    def current_position(self, ticker=None):
        """
        Return dataframe with current tickers position.

        Parameters:
            Ticker    (str): Return only for specific ticker.
                             Default: all
        """
        position_df = (
            self.fiitransactions.transactions(ticker).groupby("Ticker").tail(1).copy()
        )

        # Filter out historical tickers, ie, ticker with current position is zero units
        position_df = position_df.loc[position_df["Adj Qtd"] != 0]

        # Add current quote and pct return
        position_df["Current Quote"] = position_df.apply(
            lambda x: fii_quote(x["Ticker"]).iloc[0][0], axis=1
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
            lambda x: fii_quote(x["Ticker"]).iloc[0][0], axis=1
        )
        # Calculate dividend yield for price it paid for ticker and for
        # current ticker price
        pd_df["Dividend Yield"] = (
            pd_df["Monthly Dividends"] / pd_df["Adj unit price"]
        ) * 100
        pd_df["Current Quote Dividend Yield"] = (
            pd_df["Monthly Dividends"] / pd_df["Current Quote"]
        ) * 100

        pd_df.reset_index("Date", inplace=True)
        pd_df.sort_values(
            by=["Date", "Ticker"], ascending=[sort_date_ascending, True], inplace=True
        ),
        pd_df["Date"] = pd_df["Date"].apply(lambda x: x.strftime("%Y-%b"))

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
        units_prices = pd_df.groupby("Ticker").tail(1)["Adj unit price"].sum()
        dividends = pd_df.groupby("Ticker").tail(1)["Monthly Dividends"].sum()
        div_yield = (dividends / units_prices) * 100
        return div_yield

    def total_dividend_received(self, period="Y"):
        """
        Return total dividend received.

        Parameters:
            Period      (Y/M): Y - yearly
                               M - monthy
                               default: "Y"
        """
        pd_df = self.calc_monthly_dividends()
        pd_df.set_index("Date", inplace=True)
        pd_df.index = pd.to_datetime(pd_df.index)
        pd_df = pd_df[["Amount Received"]].resample(period).sum().reset_index("Date")

        date_fmt = "%Y" if period == "Y" else "%Y %b"
        pd_df["Date"] = pd_df["Date"].dt.strftime(date_fmt)
        return pd_df


# fiiportfolio = FiiPortfolio("fii_aplicacoes.csv")
# print("################")
# print(fiiportfolio.total_dividend_received("M"))
# print("Transaction")
# print(fiiportfolio.fiitransactions.transactions())
# print("################")
# print("monthly position")
# print(fiiportfolio.monthly_position())
# print(fiiportfolio.current_position())
# print(fiiportfolio.total_invest)
# print(fiiportfolio.total_invest_monthly)
# print("################")
# print(fiiportfolio.calc_monthly_dividends().to_string())
# print(fiiportfolio.total_dividend_yield)
