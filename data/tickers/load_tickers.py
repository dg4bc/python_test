"""Functions to variably load ticker information from web or from the local data."""

# External imports
import typing

# Local imports
from ..database_handle import DBHandle
from .via_pdf import load_russell_2000_tickers
from .via_slickcharts import load_snp_500_tickers, load_nasdaq_100_tickers

# Module level constants
SCRAPE_FUNCTION_DICTIONARY = {
    "rut": load_russell_2000_tickers,
    "snp": load_snp_500_tickers,
    "ndx": load_nasdaq_100_tickers,
}
KEY_INDEX_DICTIONARY = {"rut": "^RUT", "snp": "^GSPC", "ndx": "^NDX"}


def _database_get_ticker_table(
    target_table: str, database_handle: DBHandle
) -> typing.List[str]:
    """
    Loads the tickers of an index from the data
    :param target_table: The three character prefix string of the index
    :param database_handle: The handle to the database to be queried
    :return: The ticker strings corresponding to the argument index
    """
    return [
        item[0]
        for item in database_handle.cursor.execute(
            "".join(["SELECT * FROM " + target_table + "_tickers"])
        ).fetchall()
    ]


def _write_ticker_list_to_database(
    target_table: str, ticker_list: typing.List[str], database_handle: DBHandle
) -> None:
    """
    Stores the passed list of ticker strings in a local data
    :param target_table: The three character prefix string of the index
    :param ticker_list: A list of ticker strings to be stored
    :param database_handle: The handle to the database to be modified
    """
    # Where the data does not contain the relevant table, it is created
    database_handle.cursor.execute(
        "".join(
            [
                "CREATE TABLE IF NOT EXISTS " + target_table + "_tickers (",
                "ticker TEXT NOT NULL",
                ")",
            ]
        )
    )
    database_handle.cursor.executemany(
        "INSERT INTO " + target_table + "_tickers(ticker) VALUES(?)",
        [tuple([string]) for string in ticker_list],
    )
    database_handle.commit()


def get_index_tickers(
    index: str, database_handle: typing.Optional[DBHandle] = None
) -> typing.List[str]:
    """
    Loads the tickers corresponding to the index from data or web
    :param index: The three character prefix string of the index
    :param database_handle: Optionally pass an open database handle to avoid reopening
    :return: The ticker strings corresponding to the argument index
    """
    # Where a data handle is passed, that open handle is reused
    close_database = False
    if database_handle is None:
        close_database = True
        database_handle: DBHandle = DBHandle()
    if database_handle.contains_table(index + "_tickers"):
        tickers = _database_get_ticker_table(index, database_handle)
        if close_database:
            del database_handle
        return tickers
    scrape_function = SCRAPE_FUNCTION_DICTIONARY.get(index)
    if scrape_function is None:
        raise ValueError(f"The passed argument {index} was not a known index key.")
    tickers = scrape_function()
    tickers.append(KEY_INDEX_DICTIONARY.get(index))
    _write_ticker_list_to_database(index, tickers, database_handle)
    if close_database:
        del database_handle
    return tickers


def get_all_tickers() -> typing.List[str]:
    """
    Loads all unique tickers of, and constituting, the three target indices
    :return: The unique ticker strings
    """
    database_handle: DBHandle = DBHandle()
    aggregate_tickers: typing.Set[str] = set([])
    for key in SCRAPE_FUNCTION_DICTIONARY:
        aggregate_tickers.update(set(get_index_tickers(key, database_handle)))
    del database_handle
    return list(aggregate_tickers)
