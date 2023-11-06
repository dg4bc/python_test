"""Creation and parsing of a numeric slider representing a range of dates."""

# External imports
import typing
import datetime
import dash

# Creation of a numerical date mapping to facilitate creating a date range slider
start_date: datetime.date = datetime.date(2010, 1, 1)
end_date: datetime.date = datetime.date(2019, 12, 31)
date_options: typing.List[str] = [
    (start_date + datetime.timedelta(days=index)).strftime("%Y-%m-%d")
    for index in range((end_date - start_date).days + 1)
]


date_slider: dash.dcc.RangeSlider = dash.dcc.RangeSlider(
    id="date-range-slider",
    min=0,
    max=len(date_options) - 1,
    step=1,
    value=[len(date_options) - 366, len(date_options) - 1],
    marks=dict(list(enumerate(date_options))[::365]),
)


def dates_from_range_references(references: typing.List[int]) -> typing.List[str]:
    """
    Parse date references from the range slider to corresponding dates
    :param references: Integer references of dates selected in interface
    :return: Datetime strings referenced by the argument indices
    """
    return [date_options[reference] for reference in references]
