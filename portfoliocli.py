#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Command line interface for my investments tracker."""

import argparse
import logging
import sys

from portfolio.fii import FiiPortfolio


##############################################################################
# Command line parser
##############################################################################
def parse_parameters():
    """Command line parser."""
    epilog = """
    Exemplos de uso:
        %(prog)s -h
        %(prog)s fii -h
        %(prog)s fii -p
    """
    parser = argparse.ArgumentParser(
        description="My investments tracker command line",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", dest="debug", help="debug flag"
    )

    # Add subcommands options
    subparsers = parser.add_subparsers(title="Commands", dest="command")
    # fii
    fii_parser = subparsers.add_parser("fii", help="Portfolio FII information")
    fii_group = fii_parser.add_mutually_exclusive_group(required=True)
    fii_group.add_argument(
        "-p",
        "--position",
        dest="position",
        action="store_true",
        help="Show Current Position",
    )
    fii_group.add_argument(
        "-d",
        "--dividends",
        dest="dividends",
        action="store_true",
        help="Show Dividends",
    )
    fii_group.add_argument(
        "-t",
        "--transactions",
        dest="transactions",
        action="store_true",
        help="Show Transactions",
    )
    fii_group.add_argument(
        "-m",
        "--monthly",
        dest="monthly",
        action="store_true",
        help="Show Position Monthly",
    )

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    return parser.parse_args()


def setup_logging(logfile=None, *, filemode="a", date_format=None, log_level="DEBUG"):
    """
    Configure logging.

    Arguments (opt):
        logfile     (str): log file to write the log messages
                               If not specified, it shows log messages
                               on screen (stderr)
    Keyword arguments (opt):
        filemode    (a/w): a - log messages are appended to the file (default)
                           w - log messages overwrite the file
        date_format (str): date format in strftime format
                           default is %m/%d/%Y %H:%M:%S
        log_level   (str): specifies the lowest-severity log message
                           DEBUG, INFO, WARNING, ERROR or CRITICAL
                           default is DEBUG
    """
    dict_level = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    if log_level not in dict_level:
        raise ValueError("Invalid log_level")
    if filemode not in ["a", "w"]:
        raise ValueError("Invalid filemode")

    if not date_format:
        date_format = "%m/%d/%Y %H:%M:%S"

    log_fmt = "%(asctime)s %(module)s %(funcName)s %(levelname)s %(message)s"

    logging.basicConfig(
        level=dict_level[log_level],
        format=log_fmt,
        datefmt=date_format,
        filemode=filemode,
        filename=logfile,
    )

    return logging.getLogger(__name__)


##############################################################################
# Main function
##############################################################################
def main():
    """Command line execution."""
    global log

    # Parser the command line
    args = parse_parameters()
    # Configure log --debug
    log = setup_logging() if args.debug else logging
    log.debug("CMD line args: %s", vars(args))

    fiiportfolio = FiiPortfolio("fii_transactions.csv")

    if args.position:
        print(fiiportfolio.current_position().to_string())
    if args.dividends:
        print(fiiportfolio.calc_monthly_dividends().to_string())
    if args.transactions:
        print(fiiportfolio.fiitransactions.transactions())
    if args.monthly:
        print(fiiportfolio.monthly_position())


##############################################################################
# Run from command line
##############################################################################
if __name__ == "__main__":
    main()

# vim: ts=4
