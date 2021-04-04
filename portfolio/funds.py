# -*- coding: utf-8 -*-
# pylint: disable=no-member
"""Funds Tracker."""

import datetime
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

import requests

from .portutils import Singleton


# CVM url to download performance funds files
URL_INFORME_DIARIO = "http://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS"

# Directory to store cvm data files
CSV_FILES_DIR = "myfiles/cvm_data"

# Default funds portfolio csv file
# It is used if transaction file is not set
# on environment variable FUNDS_TRANSACTIONS
CSV_FILE = "example_transactions/funds_transactions.csv"


def create_dir(dir_name):
    """
    Create a local directory. It supports nested directory.

    Params:
        dir_name   (str): Directory to create
    """
    # Check if dir_name already exist
    if os.path.exists(dir_name):
        if os.path.isfile(dir_name):
            print("Error: path {} exists and is not a directory".format(dir_name))
            sys.exit(1)
    else:
        try:
            os.makedirs(dir_name)
        except PermissionError:
            print("Error: PermissionError to create dir {}".format(dir_name))
            sys.exit(1)


def download_file(url, local_file, *, allow_redirects=True, decode=True):
    """
    Download a file.

    Arguments:
        url                    (str): URL to download
        local_file             (str): Local filename to store the downloaded
                                      file

    Keyword arguments (opt):
        allow_redirects (True/False): Allow request to redirect url
                                      default: True
        decode          (True/False): Decode compressed responses like gzip
                                      default: True

    Return:
        Request response
    """
    with requests.get(url, stream=True, allow_redirects=allow_redirects) as res:
        if decode:
            res.raw.decode_content = True

        if res.status_code == 200:
            print("Downloading arquivo: {}...".format(local_file))
            with open(local_file, "wb") as fd:
                shutil.copyfileobj(res.raw, fd)

    return res


class FundsPortfolio(metaclass=Singleton):
    """Class to handle Brazilian funds."""

    def __init__(self, filename=None):
        """Initialize funds porfolio class."""
        self.fundscvm = FundsCvm()
        self.transactions_df = None
        self.historical_df = None
        self.filename = (
            filename if filename else os.getenv("FUNDS_TRANSACTIONS", CSV_FILE)
        )
        print("Funds file: ", self.filename)

        self.load_transactions()
        self.get_cvm_data()
        self.add_cvm_data_to_transactions()

    def load_transactions(self):
        """Create dataframe with csv transaction file."""
        print("Creating transactions dataframe")
        self.transactions_df = pd.read_csv(
            self.filename,
            sep=";",
            encoding="UTF-8",
            parse_dates=["Date"],
            dayfirst=True,
            thousands=".",
            decimal=",",
        )
        self.transactions_df.sort_values(["Date"], ascending=[True], inplace=True)
        # If operation is "Venda", convert value to negative
        self.transactions_df["Value"] = self.transactions_df.apply(
            lambda x: -x["Value"] if x["Operation"] == "Venda" else x["Value"],
            axis="columns",
        )
        self.transactions_df["Adj Value"] = self.transactions_df.groupby("Cnpj")[
            "Value"
        ].cumsum()

    def get_cvm_data(self):
        """Download and create dataframe from CVM."""
        print("Getting cvm data")
        pd_df = self.transactions_df.groupby("Cnpj").head(1)
        # Download files for each fund
        for _, row in pd_df.iterrows():
            self.fundscvm.create_fund_df(row.Cnpj, row.Date.strftime("%Y%m"))

    def add_cvm_data_to_transactions(self):
        """Add quote value to transaction table."""
        print("Adding cvm data to transaction dataframe")
        self.transactions_df["Quote Value"] = self.transactions_df.apply(
            lambda x: self.fundscvm.fund_quote_date(
                x["Cnpj"], x["Date"].strftime("%Y-%m-%d")
            ),
            axis=1,
        )
        self.transactions_df["Num Cota"] = (
            self.transactions_df["Value"] / self.transactions_df["Quote Value"]
        )
        self.transactions_df["Adj Num Cota"] = self.transactions_df.groupby("Cnpj")[
            "Num Cota"
        ].cumsum()

    def transactions(self, fund_name=None):
        """
        Return dataframe with all transactions.

        Parameters:
            fund_name    (str): Return only operation for specific Fund.
                                Default: all
        """
        if fund_name:
            return self.transactions_df[self.transactions_df["Fund Name"] == fund_name]
        else:
            return self.transactions_df

    def money_invested_monthly(self):
        """Return dataframe with amount of money invested monthly."""
        pd_df = self.transactions()
        return (
            pd_df.groupby(pd_df["Date"].dt.strftime("%Y-%m"))[["Value"]]
            .sum()
            .reset_index("Date")
        )

    def amount_invested_by_cnpj(self):
        """Return amount invested."""
        return self.transactions_df.groupby("Cnpj").tail(1)[
            ["Date", "Cnpj", "Adj Value"]
        ]

    def current_position_by_cnpj(self):
        """Return current investment position."""
        if self.historical_df is None:
            self.join_transactions_and_cvm_data()

        pd_df = (
            self.historical_df.groupby("Cnpj")
            .tail(1)[
                [
                    "Cnpj",
                    "Fund Name",
                    "Adj Value",
                    "Historical Position",
                    "Historical Perf",
                ]
            ]
            .copy()
        )
        return pd_df.rename(
            columns={
                "Historical Position": "Current Position",
                "Historical Perf": "Gain/Loss Pct",
            }
        )

    @property
    def total_invest(self):
        """
        Return total amount invested and the current holdings value.

        Return tuple:
            (amount invested, current position)
        """
        return (
            self.amount_invested_by_cnpj()["Adj Value"].sum(),
            self.current_position_by_cnpj()["Current Position"].sum(),
        )

    @property
    def total_return(self):
        """Return current performance pct."""
        return_pct = ((self.total_invest[1] / self.total_invest[0]) - 1) * 100
        return return_pct

    def join_transactions_and_cvm_data(self):
        """Add to transaction dataframe quote value and adj number of quotes."""
        if self.historical_df is not None:
            return self.historical_df
        self.historical_df = pd.DataFrame()

        for cnpj in self.transactions_df["Cnpj"].unique().tolist():
            # Create a dataframe with only data regarding the cnpj
            pd_tmp_df = self.transactions_df.loc[self.transactions_df["Cnpj"] == cnpj]
            pd_tmp_df.set_index("Date", inplace=True)
            # Create a dataframe with historical quotes for the cnpj
            informe_pd_df = self.fundscvm.fund_quotes_all(cnpj).copy()
            informe_pd_df.drop(["CNPJ Fundo"], axis="columns", inplace=True)
            informe_pd_df.set_index("Date", inplace=True)

            hist_tmp_df = pd.concat([pd_tmp_df, informe_pd_df], axis="columns")
            hist_tmp_df.fillna(method="ffill", inplace=True)
            hist_tmp_df.dropna(inplace=True)
            hist_tmp_df.reset_index("Date", inplace=True)
            hist_tmp_df["Historical Position"] = (
                hist_tmp_df["Adj Num Cota"] * hist_tmp_df["Valor Cota"]
            )
            hist_tmp_df["Historical Perf"] = (
                (hist_tmp_df["Historical Position"] / hist_tmp_df["Adj Value"]) - 1
            ) * 100

            self.historical_df = pd.concat([self.historical_df, hist_tmp_df])

        return self.historical_df


class FundsCvm:
    """Get data from CVM and create informe DataFrame."""

    csv_columns = {
        "CNPJ_FUNDO": "CNPJ Fundo",
        "VL_QUOTA": "Valor Cota",
        "DT_COMPTC": "Date",
    }

    def __init__(self):
        """Initialize fundscvm class."""
        self.funds = {}

    @staticmethod
    def download_informe_mensal(file_name):
        """
        Download do arquivo csv com informe mensal.

        Parametros:
            file_name     (str): Informe file name

        Return:
            (str): path local file
        """
        url = "{}/{}".format(URL_INFORME_DIARIO, file_name)
        local_file = "{}/{}".format(CSV_FILES_DIR, file_name)
        print("downloading url: ", url, os.getpid())

        if os.path.exists(local_file):
            print("Local file already exist: ", file_name)
            return local_file

        res = download_file(url, local_file)
        if res.status_code == 404:
            print("File not found on cvm site: ", url)
        elif res.status_code == 200:
            print("File downloaded successfully: ", file_name)
            return local_file
        else:
            print("download resposnse: %s", res)

        return

    def create_fund_df(self, cnpj, start_date):
        """
        Create dataframe with daily quote values for a fund.

        Dataframe create from start_date till today

        Parameters:
            cnpj               (str): fund CNPJ
            start_date  (str YYYYMM): The first month to gather fund
                                      quote values
        """
        end_date = datetime.datetime.today().date()
        months = (
            pd.period_range(start_date, end_date, freq="M").strftime("%Y%m").to_list()
        )
        informe_files = ["inf_diario_fi_{}.csv".format(m) for m in months]

        create_dir(CSV_FILES_DIR)

        with ThreadPoolExecutor(max_workers=2) as executor:
            result = executor.map(self.download_informe_mensal, informe_files)

        cnpj_local_files = [f for f in result if f is not None]

        pd_df = pd.DataFrame()
        # For each file, create dataframe, filter cnpj and append to pd_df
        for file_name in cnpj_local_files:
            pd_tmp_df = pd.read_csv(
                file_name,
                sep=";",
                encoding="ISO-8859-1",
                usecols=["CNPJ_FUNDO", "VL_QUOTA", "DT_COMPTC"],
                parse_dates=["DT_COMPTC"],
            )

            pd_tmp_df = pd_tmp_df.loc[pd_tmp_df["CNPJ_FUNDO"] == cnpj]
            pd_tmp_df.rename(columns=self.csv_columns, inplace=True)
            pd_df = pd.concat([pd_df, pd_tmp_df])

        pd_df.sort_values("Date", ascending=True, inplace=True)
        self.funds[cnpj] = pd_df

    def fund_quote_date(self, cnpj, date):
        """Return fund quote for a specific date."""
        pd_df = self.funds[cnpj]
        print("Geeting fund quote:", cnpj, date)
        return pd_df.loc[pd_df["Date"] == date]["Valor Cota"].values[0]

    def fund_quotes_all(self, cnpj):
        """Return quote funs for all days."""
        return self.funds[cnpj]


# vim: ts=4
