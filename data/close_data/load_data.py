"""Provides a function for loading prices either locally where present, or from web"""

# External imports
import typing
import pandas

# Local imports
from ..database_handle import DBHandle
from ..tickers import get_index_tickers, get_all_tickers
from .from_database import load_database_close_prices
from .from_yfinance import load_yfinance_close_prices


def get_close_prices(
    start_date: str,
    end_date: str,
    index: typing.Optional[str] = None,
    tickers: typing.Optional[typing.List[str]] = None,
    local_exclusive: bool = False,
) -> pandas.DataFrame:
    """
    Loads close prices for a date range, optionally for a specific index target
    Note where argument ranges exceed database stored ranges, the whole range will be re-downloaded.
    This as complete local / download combination logic needing query storage was not implemented.
    :param start_date: Inclusive YYYY-MM-DD date representation of target range start
    :param end_date: Exclusive YYYY-MM-DD date representation of target range end
    :param index: Optional three character prefix string of the index, None for all
    :param tickers: Optional list of specific tickers to load, combining with index via AND
    :param local_exclusive: Where True no new data will be downloaded, defaults to False
    :return: A wide format pandas dataframe of the loaded data
    """
    database_handle = DBHandle()
    target_tickers: typing.List[str] = (
        get_all_tickers()
        if index is None
        else get_index_tickers(index, database_handle)
    )
    if tickers is not None:
        target_tickers: typing.List[str] = [
            ticker for ticker in target_tickers if ticker in tickers
        ]
    if database_handle.contains_table("closes"):
        loaded_data: pandas.DataFrame = load_database_close_prices(
            target_tickers, start_date, end_date, database_handle
        )
    else:
        loaded_data: pandas.DataFrame = pandas.DataFrame()
    if local_exclusive:
        return loaded_data
    missing_tickers: typing.List[str] = list(
        set(target_tickers) - set(loaded_data.columns.values)
    )
    downloaded_data: pandas.DataFrame = load_yfinance_close_prices(
        list(missing_tickers), start_date, end_date, database_handle
    )
    if downloaded_data.empty:
        return loaded_data
    return pandas.concat([loaded_data, downloaded_data], axis="columns")
