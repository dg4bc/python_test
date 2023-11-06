"""A Dash app which regresses index movements from a limited number of index components
This file is in two parts. At the top a Dash user interface is defined.
Below this, three callbacks manage updates to the Dash application.
These callbacks are roughly sequential, from data selection through result visualisation.
Finally, the application is run."""

# External imports
import ast
import dash
import pandas
from dash.dependencies import Input, Output, State, ALL
from sklearn.linear_model import LinearRegression
from sklearn.feature_selection import RFE

# Local imports
from data import get_index_tickers, get_close_prices
from dashboard import (
    date_slider,
    dates_from_range_references,
    grid_from_label_element_widths,
)

app = dash.Dash(__name__)

# Specification of the Dash Store components which will be used
data_store_identifiers = [
    "present-buttons",  # What ticker buttons are in the interface
    "selected-buttons",  # The reference integers of selected ticker buttons
    "selected-tickers",  # The selected ticker strings
    "growth-buttons",  # References of the highest growth tickers
    "volatility-buttons",  # References of the highest volatility tickers
    "explain-buttons",  # References of the best tickers to approximate the index
]

# Specification of the tabular interface elements at the top of the page
tabular_interface_elements = [
    (
        "Range selection:",
        date_slider,
        "800px",
    ),
    (
        "Index selection:",
        dash.dcc.Dropdown(
            id="index-dropdown",
            options=[
                {"label": "S&P 500", "value": "snp"},
                {"label": "NASDAQ 100", "value": "ndx"},
                {"label": "Russell 2000", "value": "rut"},
            ],
            value="ndx",
        ),
        "200px",
    ),
    (
        "Component count:",
        dash.dcc.Input(
            id="component-count",
            type="number",
            min=1,
            max=10,
            value=5,
        ),
        "200px",
    ),
    (
        "Select components:",
        [
            dash.html.Button(label, id=f"select-{label}", n_clicks=0)
            for label in ["alphabetical", "growth", "volatility", "explain"]
        ],
        "300px",
    ),
    (
        "Selected components:",
        dash.html.Div(
            id="selected-components",
        ),
        "300px",
    ),
    (
        "Regression results:",
        dash.html.Div(
            id="regression-explanation",
        ),
        "300px",
    ),
]

app.layout = dash.html.Div(
    # Creation of specified data stores
    [dash.dcc.Store(id=identifier, data=[]) for identifier in data_store_identifiers]
    + [
        # Population of a grid layout of the tabular interface elements
        grid_from_label_element_widths(tabular_interface_elements),
        # An element to store generated ticker selection buttons
        dash.html.Div(id="button-container"),
        # Graph elements for resultant visualisations
        dash.dcc.Graph(id="regression-plot"),
        dash.dcc.Graph(id="emulation-plot"),
        dash.dcc.Graph(id="component-plot"),
    ]
)


@app.callback(
    Output("present-buttons", "data"),
    Output("volatility-buttons", "data"),
    Output("growth-buttons", "data"),
    Output("explain-buttons", "data"),
    Output("button-container", "children"),
    Input("index-dropdown", "value"),
    Input("date-range-slider", "value"),
    Input("component-count", "value"),
)
def update_range_index_state(index_key, date_references, component_count):
    """
    A callback responds to updated domain, i.e. date range and index, updating selection presets
    :param index_key: The index selected in the user interface
    :param date_references: The integer references of the dates selected in the interface
    :param component_count: The maximum component integer from the interface
    :return: Updates present button list, references for component selections, and buttons
    """
    if index_key is None:
        return dash.no_update, dash.no_update

    # Loading relevant data and validating complete data presence for target index tickers
    close_prices = get_close_prices(
        *dates_from_range_references(date_references),
        index_key,
        local_exclusive=True,
    ).dropna(axis="columns")
    close_tickers = close_prices.columns.values
    valid_tickers = sorted(
        [
            ticker
            for ticker in get_index_tickers(index_key)[:-2]
            if ticker in close_tickers
        ]
    )

    # Naming validated subsets of the loaded data for selection computation
    index_close_prices = close_prices[close_tickers[-1]]
    close_prices = close_prices[valid_tickers]
    price_changes = close_prices.pct_change().dropna()

    # Volatile references from naive volatility values, as scaling is discarded
    volatile_ordering = price_changes.std().argsort()[::-1][:component_count]

    # Growth references via the start and finish price ratios
    growth_ordering = (close_prices.iloc[-1] / close_prices.iloc[0]).argsort()[::-1][
        :component_count
    ]

    # References for feature selection via recursive feature elimination on linear regression
    linear_model = LinearRegression()
    recursive_feature_elimination = RFE(
        linear_model, n_features_to_select=component_count
    )
    explain_features = [
        index
        for index, boolean in enumerate(
            recursive_feature_elimination.fit(
                price_changes, index_close_prices.pct_change().dropna()
            ).support_
        )
        if boolean
    ]

    # Populating buttons which allow manual ticker selection
    buttons = [
        dash.html.Button(ticker, id={"type": "dyn-button", "index": index})
        for index, ticker in enumerate(valid_tickers)
    ]
    div = dash.html.Div(
        buttons,
        style={
            "display": "grid",
            "grid-template-columns": "repeat(20, 1fr)",
            "gap": "0px",
            "alignItems": "center",
            "justifyItems": "start",
        },
    )
    return valid_tickers, volatile_ordering, growth_ordering, explain_features, div


# pylint: disable=too-many-arguments
@app.callback(
    Output("selected-buttons", "data"),
    Output("selected-tickers", "data"),
    Output("selected-components", "children"),
    Input({"type": "dyn-button", "index": ALL}, "n_clicks"),
    Input("select-alphabetical", "n_clicks"),
    Input("select-growth", "n_clicks"),
    Input("select-volatility", "n_clicks"),
    Input("select-explain", "n_clicks"),
    Input("component-count", "value"),
    State("selected-buttons", "data"),
    State("present-buttons", "data"),
    State("selected-tickers", "data"),
    State("growth-buttons", "data"),
    State("volatility-buttons", "data"),
    State("explain-buttons", "data"),
    prevent_initial_callback=True,
)
def update_selection_state(
    _a,
    _b,
    _c,
    _d,
    _e,
    component_count,
    selected_buttons,
    present_buttons,
    tickers_state,
    growth_buttons,
    volatility_buttons,
    explain_buttons,
):
    """
    A callback which updates the interface to updated selection, i.e. clicked tickers or presets
    :param _a: Unused data, input trigger from button clicks
    :param _b: Unused data, input trigger from alphabetical selection button
    :param _c: Unused data, input trigger from growth selection button
    :param _d: Unused data, input trigger from volatility selection button
    :param _e: Unused data, input trigger from explain selection button
    :param component_count: The maximum component integer from the interface
    :param selected_buttons: The references of selected buttons
    :param present_buttons: The tickers corresponding to buttons in the interface
    :param tickers_state: The presently selected tickers in the interface
    :param growth_buttons: References of buttons with maximal growth tickers
    :param volatility_buttons: References of buttons with maximal volatility tickers
    :param explain_buttons: References of buttons for tickers which best explain the index
    :return: Updates to selected ticker lists and their references, and an interface string
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update
    triggering_identifier = ctx.triggered[0]["prop_id"]
    button_id = triggering_identifier.split(".")[0]
    if "index-dropdown" in button_id:
        return [], [], []
    if "dyn-button" in button_id:
        button_index = ast.literal_eval(button_id)["index"]
        if button_index in selected_buttons:
            selected_buttons.remove(button_index)
        else:
            selected_buttons.append(button_index)
    if "alphabetical" in button_id:
        selected_buttons = list(range(component_count))
    if "growth" in button_id:
        selected_buttons = growth_buttons
    if "volatility" in button_id:
        selected_buttons = volatility_buttons
    if "explain" in button_id:
        selected_buttons = explain_buttons
    while len(selected_buttons) > component_count:
        selected_buttons.pop(0)
    selected_tickers = [
        present_buttons[index]
        for index in selected_buttons
        if index < len(present_buttons)
    ]
    if tickers_state == selected_tickers:
        return dash.no_update, dash.no_update, dash.no_update
    return selected_buttons, selected_tickers, ", ".join(selected_tickers)


@app.callback(
    Output("regression-explanation", "children"),
    Output("regression-plot", "figure"),
    Output("emulation-plot", "figure"),
    Output("component-plot", "figure"),
    Input("date-range-slider", "value"),
    Input("selected-tickers", "data"),
    State("index-dropdown", "value"),
    prevent_initial_callback=True,
)
def update_output(date_references, selected_tickers, index_key):
    """
    A callback which updates output from updated interface state, i.e. new tickers or data
    :param date_references: The integer references of the dates selected in the interface
    :param selected_tickers: The presently selected tickers in the interface
    :param index_key: The index selected in the user interface
    :return: Updates the regression coefficient table, and the three explanatory graphs
    """
    if index_key is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not selected_tickers:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # Load the specified data
    close_prices = get_close_prices(
        *dates_from_range_references(date_references),
        index_key,
        local_exclusive=True,
    )

    # Store the index reference and compute price movements
    index_ticker = close_prices.columns.values[-1]
    combined_price_movements = (
        close_prices[selected_tickers + [index_ticker]].pct_change().dropna()
    )

    # Fit a linear regression to best approximate the index from the tickers
    linear_model = LinearRegression().fit(
        combined_price_movements[selected_tickers],
        combined_price_movements[index_ticker],
    )
    # noinspection PyUnresolvedReferences
    linear_forecast = linear_model.predict(combined_price_movements[selected_tickers])

    # Populate a table for the user interface to show the regressed coefficients
    # noinspection PyUnresolvedReferences
    linear_coefficients = pandas.DataFrame(
        {
            "Feature": selected_tickers,
            "Coefficient": linear_model.coef_.round(3),
        }
    )
    coefficient_table = dash.dash_table.DataTable(
        id="table",
        columns=[{"name": index, "id": index} for index in linear_coefficients.columns],
        data=linear_coefficients.to_dict("records"),
    )

    # Reconstruct the aggregate index approximation from the regressed price movements
    forecast_index_proxy = [close_prices[index_ticker].iloc[0]]
    for forecast_change in linear_forecast:
        forecast_index_proxy.append(forecast_index_proxy[-1] * (1 + forecast_change))
    forecast_index_proxy = pandas.Series(forecast_index_proxy)

    # Build figures expressing the regression, the cumulative fit, and component growth
    movement_regression_figure = {
        "data": [
            {
                "x": combined_price_movements.index,
                "y": combined_price_movements[index_ticker],
                "mode": "markers",
                "name": "Index",
            },
            {
                "x": combined_price_movements.index,
                "y": linear_forecast,
                "mode": "lines",
                "name": "Approximated",
            },
        ],
        "layout": {
            "title": "Index movements against regressed approximation",
            "xaxis": {"title": "Close dates"},
            "yaxis": {"title": "Factional price movements"},
        },
    }

    index_proxy_figure = {
        "data": [
            {
                "x": close_prices.index,
                "y": close_prices[index_ticker],
                "mode": "lines",
                "name": "Index",
            },
            {
                "x": close_prices.index,
                "y": forecast_index_proxy,
                "mode": "lines",
                "name": "Approximated",
            },
        ],
        "layout": {
            "title": "Index price evolution against regressed approximation",
            "xaxis": {"title": "Close dates"},
            "yaxis": {"title": "Close prices"},
        },
    }

    component_figure = {
        "data": [
            {
                "x": close_prices.index,
                "y": close_prices[index_ticker] / close_prices[index_ticker].iloc[0],
                "mode": "markers",
                "name": "Index",
            },
            {
                "x": close_prices.index,
                "y": forecast_index_proxy / forecast_index_proxy.iloc[0],
                "mode": "lines",
                "name": "Approximated",
            },
        ]
        + [
            {
                "x": close_prices.index,
                "y": close_prices[ticker] / close_prices[ticker].iloc[0],
                "mode": "lines",
                "name": ticker,
            }
            for ticker in selected_tickers
        ],
        "layout": {
            "title": "Comparison of component price growth",
            "xaxis": {"title": "Close dates"},
            "yaxis": {"title": "Price proportion"},
        },
    }

    return (
        coefficient_table,
        movement_regression_figure,
        index_proxy_figure,
        component_figure,
    )


if __name__ == "__main__":
    app.run_server(debug=True)
