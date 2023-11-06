"""Functions which scrape index constituent tickers from slickcharts.com component listings."""

# External imports
import collections
import typing
import cfscrape
import bs4

# Module level constants
TARGET_PREFIX = "/symbol/"
TARGET_PREFIX_LENGTH = len(TARGET_PREFIX)
URL_PREFIX = "https://www.slickcharts.com/"


def _load_suffix_tickers(suffix: str) -> typing.List[str]:
    """
    A module local utility which scrapes index ticker strings from a slickcharts.com subdomain
    :return: The list of ticker strings of the target index constituents in arbitrary ordering
    """

    # Specific tools are required to access and parse the site programmatically
    scraper: cfscrape.CloudflareScraper = cfscrape.create_scraper()
    page_contents: bs4.BeautifulSoup = bs4.BeautifulSoup(
        scraper.get(URL_PREFIX + suffix).content, features="html.parser"
    )

    # The tickers are all present on the page as duplicate URL suffixes
    hyperlinks = [link.get("href") for link in page_contents.findAll("a")]
    symbol_strings = [
        href[TARGET_PREFIX_LENGTH:]
        for href in hyperlinks
        if href[:TARGET_PREFIX_LENGTH] == TARGET_PREFIX
    ]
    target_symbols = [
        item for item, count in collections.Counter(symbol_strings).items() if count > 1
    ]
    return target_symbols


def load_snp_500_tickers() -> typing.List[str]:
    """
    Scrapes S&P500 constituent ticker strings from slickcharts.com
    :return: The list of ticker strings of the S&P500 constituents in arbitrary ordering
    """
    return _load_suffix_tickers("sp500")


def load_nasdaq_100_tickers() -> typing.List[str]:
    """
    Scrapes NASDAQ 100 constituent ticker strings from slickcharts.com
    :return: The list of ticker strings of the NASDAQ 100 constituents in arbitrary ordering
    """
    return _load_suffix_tickers("nasdaq100")
