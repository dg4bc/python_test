"""Function for loading close pricing data from a local database"""

# External imports
import typing
import datetime
import pandas

# Local imports
from ..database_handle import DBHandle


def load_database_close_prices(
    tickers: typing.List[str], start_date: str, end_date: str, database_handle: DBHandle
) -> pandas.DataFrame:
    """
    Load any relevant data for argument tickers and date range from the argument database
    :param tickers: A list of tickers for which data is sought
    :param start_date: Inclusive YYYY-MM-DD date representation of target range start
    :param end_date: Exclusive YYYY-MM-DD date representation of target range end
    :param database_handle: The handle to the database to be queried
    :return: A wide format pandas dataframe of the loaded data
    """
    loaded_dataframe = pandas.DataFrame(
        database_handle.cursor.execute(
            "".join(
                [
                    "SELECT DISTINCT * FROM closes WHERE ",
                    "ticker in ('",
                    "','".join(tickers),
                    "') AND Date >= '",
                    start_date,
                    "' AND Date < '",
                    end_date,
                    "'",
                ]
            )
        ).fetchall(),
        columns=["Date", "ticker", "price"],
    )
    loaded_dataframe = loaded_dataframe.pivot(
        index="Date", columns="ticker", values="price"
    )
    loaded_dataframe.dropna(how="all", axis=1, inplace=True)
    loaded_dataframe.index = pandas.to_datetime(loaded_dataframe.index)
    if min(loaded_dataframe.index) > datetime.datetime.strptime(
        start_date, "%Y-%m-%d"
    ) + pandas.tseries.offsets.BDay(7):
        return pandas.DataFrame()
    if max(loaded_dataframe.index) < datetime.datetime.strptime(
        end_date, "%Y-%m-%d"
    ) - pandas.tseries.offsets.BDay(7):
        return pandas.DataFrame()
    return loaded_dataframe
