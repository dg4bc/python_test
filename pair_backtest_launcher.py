"""A Dash app which examines pair trading performance on detected stock pair relationships
This file is in two parts. At the top a Dash user interface is defined.
Below this, four callbacks manage updates to the Dash application.
These callbacks are roughly sequential, from data selection through trade specification.
Finally, the application is run."""

# External imports
import typing
import itertools
import dash
import pandas
import numpy
import statsmodels.tsa.vector_ar.vecm
from dash.dependencies import Input, Output, State

# Local imports
from data import get_close_prices
from dashboard import (
    date_slider,
    dates_from_range_references,
    grid_from_label_element_widths,
    even_grid_from_nested_elements,
)
from modelling import generate_trade_sequence, risk_free_range_performance_metrics

app = dash.Dash(__name__)

# Constant elements of the pair identification table
pair_table_columns = [
    {"name": header, "id": str(index)}
    for index, header in enumerate(
        itertools.chain(
            *[
                ["Pairing", title_string]
                for title_string in [
                    "Correlation coefficient",
                    "Cointegration criticality ratio",
                ]
            ]
        )
    )
]

# Specification of the tabular interface elements at the top of the page
tabular_interface_elements = [
    (
        "Ticker count:",
        dash.dcc.Slider(
            id="ticker-count-slider",
            min=10,
            max=3000,
            value=50,
            step=10,
            marks={i: str(i) for i in range(1, 3001) if (i + 1) % 500 == 1},
        ),
        "600px",
    ),
    (
        "Range selection:",
        date_slider,
        "600px",
    ),
    (
        "Pair identifications:",
        dash.html.Div(
            dash.dash_table.DataTable(
                id="pair-table",
                columns=pair_table_columns,
                data=[],
            ),
            id="pair-table-div",
        ),
        "600px",
    ),
    (
        "Pair selection:",
        dash.html.Div(
            id="output-cell-info",
        ),
        "600px",
    ),
    (
        "Pair growth chart:",
        dash.html.Div(dash.dcc.Graph(id="exposition-plot")),
        "900px",
    ),
    (
        "Trade specifications:",
        even_grid_from_nested_elements(
            [["", "Trade criteria", "Measurement period", "quantile"]]
            + [
                [
                    end_string,
                    dash.dcc.RadioItems(
                        id=end_string.lower() + "-radioitems",
                        options=[
                            {
                                "label": "Relative Strength",
                                "value": "relative_strength",
                            },
                            {
                                "label": "Spread Deviation",
                                "value": "spread_deviation",
                            },
                        ]
                        + (
                            [
                                {
                                    "label": "Interval",
                                    "value": "interval",
                                }
                            ]
                            if end_string != "Entry"
                            else []
                        ),
                        value="relative_strength",
                        inline=True,
                    ),
                    dash.html.Div(
                        [
                            dash.dcc.Slider(
                                id=end_string.lower() + "-period-slider",
                                min=1,
                                max=29,
                                value=15,
                                step=1,
                                marks={i: str(i) for i in range(1, 30) if i % 7 == 1},
                            )
                        ]
                    ),
                    dash.html.Div(
                        [
                            dash.dcc.Slider(
                                id=end_string.lower() + "-quantile-slider",
                                min=0.5,
                                max=1,
                                value=0.75,
                                step=0.025,
                                marks={i / 10: str(i / 10) for i in range(1, 11)},
                            )
                        ]
                    ),
                ]
                for end_string in ["Entry", "Exit"]
            ]
        ),
        "900px",
    ),
    (
        "Trade criteria:",
        dash.html.Div(id="trade-description"),
        "900px",
    ),
    (
        "Trade chart:",
        dash.html.Div(dash.dcc.Graph(id="trade-plot")),
        "900px",
    ),
    (
        "Valuation chart:",
        dash.html.Div(dash.dcc.Graph(id="valuation-plot")),
        "900px",
    ),
    (
        "Performance chart:",
        dash.html.Div(dash.dcc.Graph(id="performance-plot")),
        "900px",
    ),
]
app.layout = dash.html.Div(
    [
        dash.dcc.Store(id="selected-pair", data=[]),
        # Population of a grid layout of the tabular interface elements
        grid_from_label_element_widths(tabular_interface_elements),
    ]
)


@app.callback(
    Output("pair-table-div", "children"),
    Input("ticker-count-slider", "value"),
    Input("date-range-slider", "value"),
)
def update_range_state(ticker_count, date_references):
    """
    Responds to updated domain, i.e. date range and stock count, updating identified pair relations
    :param ticker_count: The maximum number of tickers to process, from an interface slider
    :param date_references: The date range to process, from an interface range slider
    :return: Updates a table of strongly related stock pairs via various metrics
    """
    # Loading relevant data and validating complete data presence for target index tickers
    close_prices: pandas.DataFrame = get_close_prices(
        *dates_from_range_references(date_references),
        local_exclusive=True,
    ).dropna(axis="columns")
    component_tickers: typing.List[str] = sorted(
        [ticker for ticker in close_prices.columns.values if "^" not in ticker]
    )
    if len(component_tickers) >= ticker_count:
        component_tickers = component_tickers[:ticker_count]
    component_prices: pandas.DataFrame = close_prices[component_tickers]
    component_price_movements: pandas.DataFrame = component_prices.pct_change().dropna()

    # Calculate the correlation matrix between columns, sort entries, retaining only ordered pairs
    correlation_grid: pandas.DataFrame = component_price_movements.corr().abs()
    correlations: pandas.Series = correlation_grid.unstack().sort_values(
        ascending=False
    )
    correlations: typing.List[typing.Tuple[str, str, float]] = [
        (row, column, correlation)
        for (row, column), correlation in correlations.items()
        if row > column
    ]
    correlation_upper_quartile = correlations[int(len(correlations) / 4)][-1]

    # Calculate the cointegration matrix between columns, sort entries, retaining only ordered pairs
    cointegrations: pandas.DataFrame = pandas.DataFrame(
        index=component_prices.columns,
        columns=component_prices.columns,
    )
    for col1, col2 in itertools.combinations(component_tickers, 2):
        if correlation_grid[col1][col2] >= correlation_upper_quartile:
            try:
                johansen_result = statsmodels.tsa.vector_ar.vecm.coint_johansen(
                    component_prices[[col1, col2]], det_order=0, k_ar_diff=1
                )
                criticality_ratio = (
                    johansen_result.trace_stat[0]
                    / johansen_result.trace_stat_crit_vals[0, -1]
                )
            except numpy.linalg.LinAlgError:
                criticality_ratio = 0
        else:
            criticality_ratio = 0
        cointegrations.loc[col1, col2]: float = criticality_ratio
    cointegrations: pandas.Series = cointegrations.unstack().sort_values(
        ascending=False
    )
    cointegrations: typing.List[typing.Tuple[str, str, float]] = [
        (row, column, cointegration)
        for (row, column), cointegration in cointegrations.items()
        if row > column
    ]

    # Tabulate the ten leading pairs for each measurement
    pair_table = dash.dash_table.DataTable(
        id="pair-table",
        columns=pair_table_columns,
        data=[
            dict(enumerate(row))
            for row in zip(
                *itertools.chain(
                    *[
                        (
                            [
                                " - ".join(ticker_pair)
                                for ticker_pair in zip(tickers_a, tickers_b)
                            ],
                            [round(measurement, 3) for measurement in measurements],
                        )
                        for tickers_a, tickers_b, measurements in [
                            zip(*correlations[:10]),
                            zip(*cointegrations[:10]),
                        ]
                    ]
                )
            )
        ],
    )

    return pair_table


@app.callback(
    Output("output-cell-info", "children"),
    Output("selected-pair", "data"),
    Input("pair-table", "active_cell"),
    Input("pair-table", "data"),
)
def update_selected_pair(active_cell, data):
    """
    Updates selected pairs of stocks from the pairs table for trading analysis
    :param active_cell: The triggering cell in the interface table
    :param data: The state of the table, from which ticker strings are extracted
    :return: Updates both data storage of selected stocks, and an interface string
    """
    if not active_cell:
        return "Select pairs by clicking the identification table.", []
    row = active_cell["row"]
    column_index = int(active_cell["column_id"])
    pair_string = data[row][str(column_index - column_index % 2)]
    tickers = pair_string.split(" - ")
    return pair_string, tickers


@app.callback(
    Output("exposition-plot", "figure"),
    Input("selected-pair", "data"),
    State("date-range-slider", "value"),
)
def update_pair_exposition(selected_pair, date_references):
    """
    Updates a plot showing the price relationship of the selected stock pair
    :param selected_pair: Data loaded from the interface of the two stock strings
    :param date_references: The date range to process, from an interface range slider
    :return: A logarithmic graph of pair price movements scaled to the initial minimum
    """
    if len(selected_pair) != 2:
        return {}
    close_prices = get_close_prices(
        *dates_from_range_references(date_references),
        tickers=selected_pair,
        local_exclusive=True,
    )[selected_pair]

    # Generate a growth illustrative graph for exposition
    minimum_initial = min(close_prices.iloc[0])
    pair_growth_figure = {
        "data": [
            {
                "x": close_prices.index,
                "y": numpy.log(close_prices[ticker] / minimum_initial),
                "mode": "lines",
                "name": ticker,
            }
            for ticker in selected_pair
        ],
        "layout": {
            "title": "Logarithmic comparison of pair price growth",
            "xaxis": {"title": "Close dates"},
            "yaxis": {"title": "Log price proportion"},
        },
    }
    return pair_growth_figure


# pylint: disable=too-many-arguments
@app.callback(
    Output("trade-plot", "figure"),
    Output("valuation-plot", "figure"),
    Output("performance-plot", "figure"),
    Output("trade-description", "children"),
    Input("selected-pair", "data"),
    Input("entry-radioitems", "value"),
    Input("exit-radioitems", "value"),
    Input("entry-period-slider", "value"),
    Input("exit-period-slider", "value"),
    Input("entry-quantile-slider", "value"),
    Input("exit-quantile-slider", "value"),
    State("date-range-slider", "value"),
)
def update_trade_events(
    selected_pair,
    entry_type,
    exit_type,
    entry_period,
    exit_period,
    entry_quantile,
    exit_quantile,
    date_references,
):
    """
    From interface trade structure specification, updates exposition and metrics
    :param selected_pair: Data loaded from the interface of the two stock strings
    :param entry_type: Interface specification of entry criteria type
    :param exit_type: Interface specification of exit criteria type
    :param entry_period: Interface specification of entry property measurement window length
    :param exit_period: Interface specification of exit property measurement window length
    :param entry_quantile: Interface specification of entry criteria threshold quantiles
    :param exit_quantile: Interface specification of exit criteria threshold quantiles
    :param date_references: The date range to process, from an interface range slider
    :return: Graphs of trade sequencing, portfolio value, performance metrics, and a description
    """
    if len(selected_pair) != 2:
        return {}, {}, {}, ""

    # Collate data and compute relevant price change series
    close_prices = get_close_prices(
        *dates_from_range_references(date_references),
        tickers=selected_pair,
        local_exclusive=True,
    )[selected_pair]
    prices: pandas.DataFrame = close_prices
    spreads: pandas.Series = prices.iloc[:, 1] - prices.iloc[:, 0]
    price_movements: pandas.DataFrame = prices.pct_change().dropna()
    fractional_price_spreads: pandas.Series = (
        price_movements.iloc[:, 0] - price_movements.iloc[:, 1]
    )

    # Compute entry events as per interface specification
    if entry_type == "spread_deviation":
        entry_comparison_series = spreads
        entry_string = "spread."
    else:
        entry_comparison_series = fractional_price_spreads
        entry_string = "strength."
    entry_period_means = entry_comparison_series.rolling(window=entry_period).mean()
    entry_thresholds = entry_period_means.quantile(
        entry_quantile
    ), entry_period_means.quantile(1 - entry_quantile)
    entry_string = (
        f"Positions are put on above {round(entry_quantile * 100)} "
        + f"or below {round(100 - entry_quantile * 100)} percentile "
        + entry_string
    )
    long_entry_events = [
        entry_comparison_series.index.get_loc(date)
        for date in entry_period_means[entry_period_means >= entry_thresholds[0]].index
    ]
    short_entry_events = [
        entry_comparison_series.index.get_loc(date)
        for date in entry_period_means[entry_period_means < entry_thresholds[1]].index
    ]
    entry_events = sorted(long_entry_events + short_entry_events)

    # Compute exit events as per interface specification
    if exit_type in ["spread_deviation", "relative_strength"]:
        if exit_type == "spread_deviation":
            exit_comparison_series = spreads
            exit_string = "spread."
        else:
            exit_comparison_series = fractional_price_spreads
            exit_string = "strength."
        exit_period_means = exit_comparison_series.rolling(window=exit_period).mean()
        exit_thresholds = exit_period_means.quantile(
            exit_quantile
        ), exit_period_means.quantile(1 - exit_quantile)
        exit_string = (
            f" and taken off between {round(100 - exit_quantile * 100)} "
            + f"and {round(exit_quantile * 100)} percentile "
            + exit_string
        )
        exit_events = exit_period_means[exit_thresholds[1] <= exit_period_means]
        exit_events = exit_events[exit_events < exit_thresholds[0]].index
        exit_events = [
            exit_comparison_series.index.get_loc(date) for date in exit_events
        ]
    else:
        exit_string = f" and are taken off {exit_period} days after entrance signals."
        exit_events = [entry_event + exit_period for entry_event in entry_events]
        exit_events = [
            exit_event
            for exit_event in exit_events
            if exit_event <= len(close_prices.index)
        ]

    # Remove exits which overlap with entries
    exit_events = [
        exit_event for exit_event in exit_events if exit_event not in entry_events
    ]

    # Calculate the matched entry and exit pairs where the trade would be active
    trade_references = generate_trade_sequence(entry_events, exit_events)

    # Recover the long short information related to the trade pairs
    entry_signs = [
        1 if start in long_entry_events else -1 for start, _ in trade_references
    ]

    # Run through the trade performance. This glosses over proper ratios and sizing
    portfolio_value = [(1, 0)]
    for (start, end), sign in zip(trade_references, entry_signs):
        start_value = portfolio_value[-1][0]
        for interim in range(portfolio_value[-1][1], start + 1):
            portfolio_value.append((start_value, interim))
        for increment in range(start, end + 1):
            trade_ratios = close_prices.iloc[increment] / close_prices.iloc[start]
            if sign == 1:
                trade_return = (
                    1
                    + (trade_ratios[selected_pair[0]] - trade_ratios[selected_pair[1]])
                    / 2
                )
            else:
                trade_return = (
                    1
                    + (trade_ratios[selected_pair[1]] - trade_ratios[selected_pair[0]])
                    / 2
                )
            portfolio_value.append((start_value * trade_return, increment))
    for interim in range(portfolio_value[-1][1], len(close_prices.index)):
        portfolio_value.append((portfolio_value[-1][0], interim))

    # Compute performance metrics
    portfolio_series = pandas.DataFrame(
        zip(
            [value for value, _ in portfolio_value],
            close_prices.index[[index for _, index in portfolio_value]],
        ),
        columns=["Value", "Date"],
    )
    portfolio_series.set_index("Date", inplace=True)
    performance_metrics = risk_free_range_performance_metrics(portfolio_series["Value"])

    # Construct a visualisation of the trade entry and exit on the prices
    trade_visualisation_figure = {
        "data": [
            {
                "x": close_prices.index,
                "y": close_prices[ticker],
                "mode": "lines",
                "name": ticker,
            }
            for ticker in selected_pair
        ],
        "layout": {
            "title": "Exposition of spread trade on price evolution (blue long, red short)",
            "xaxis": {"title": "Close dates"},
            "yaxis": {"title": "Component price"},
            "shapes": [
                {
                    "type": "rect",
                    "xref": "x",
                    "yref": "paper",
                    "x0": close_prices.index[start],
                    "y0": 0,
                    "x1": close_prices.index[end],
                    "y1": 1,
                    "fillcolor": "blue" if sign == 1 else "red",
                    "opacity": 0.3,
                    "line_width": 0,
                }
                for (start, end), sign in zip(trade_references, entry_signs)
            ],
        },
    }

    # Construct a visualisation of the portfolio value
    portfolio_visualisation_figure = {
        "data": [
            {
                "x": close_prices.index[[index for _, index in portfolio_value]],
                "y": [value for value, _ in portfolio_value],
                "mode": "lines",
            }
        ],
        "layout": {
            "title": "Portfolio valuation over time",
            "xaxis": {"title": "Close dates"},
            "yaxis": {"title": "Portfolio value"},
        },
    }

    # Plot performance metrics against potential risk-free rates
    performance_figure = {
        "data": [
            {
                "x": [risk_free for risk_free, *_ in performance_metrics],
                "y": metrics,
                "mode": "lines",
                "name": name,
            }
            for name, metrics in zip(
                ["Excess return", "Sharpe", "Sortino"],
                list(zip(*performance_metrics))[1:],
            )
        ],
        "layout": {
            "title": "Portfolio performance metrics against risk-free rates",
            "xaxis": {"title": "Risk-free rate"},
            "yaxis": {"title": "Metric"},
        },
    }
    return (
        trade_visualisation_figure,
        portfolio_visualisation_figure,
        performance_figure,
        entry_string + exit_string,
    )


if __name__ == "__main__":
    app.run_server(debug=True)
