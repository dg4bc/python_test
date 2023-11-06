"""This example script loads ten years of data, storing it in a local database"""

# Local imports
from data import get_close_prices

get_close_prices("2010-01-01", "2020-01-01", local_exclusive=False)
