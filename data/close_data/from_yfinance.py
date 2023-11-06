"""A function loading daily close prices from yfinance and locally storing results"""

# External imports
import typing
import yfinance
import pandas

# Local imports
from ..database_handle import DBHandle


def load_yfinance_close_prices(
    tickers: typing.List[str], start_date: str, end_date: str, database_handle: DBHandle
) -> pandas.DataFrame:
    """
    Load relevant data for argument tickers and date range from yfinance API to database
    :param tickers: A list of tickers for which data is sought
    :param start_date: Inclusive YYYY-MM-DD date representation of target range start
    :param end_date: Exclusive YYYY-MM-DD date representation of target range end
    :param database_handle: The handle to the database the data is saved to
    :return: A wide format pandas dataframe of the loaded data
    """
    # Manually assert the table, pandas to_sql does not enforce key uniqueness
    database_handle.cursor.execute(
        "".join(
            [
                "CREATE TABLE IF NOT EXISTS closes (",
                "Date TEXT NOT NULL,",
                "ticker TEXT NOT NULL,",
                "price REAL,",
                "PRIMARY KEY(Date, ticker)",
                ")",
            ]
        )
    )
    loaded_dataframe = yfinance.download(
        tickers=tickers, start=start_date, end=end_date, interval="1d"
    )["Close"]
    long_dataframe = pandas.melt(
        loaded_dataframe.reset_index(),
        id_vars="Date",
        value_vars=tickers,
        var_name="ticker",
        value_name="price",
    )

    # A staging table is used to prevent duplication in the database
    long_dataframe.to_sql(
        "staging", database_handle.connection, if_exists="replace", index=False
    )
    database_handle.cursor.execute(
        "INSERT OR REPLACE INTO closes SELECT * FROM staging"
    )
    database_handle.commit()

    loaded_dataframe.dropna(how="all", axis=1, inplace=True)
    loaded_dataframe.index = pandas.to_datetime(loaded_dataframe.index)
    return loaded_dataframe
