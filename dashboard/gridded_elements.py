"""A utility function for creating grids from lists of labels and elements"""

# External imports
import typing
import dash


def grid_from_label_element_widths(
    label_element_widths: typing.List[typing.Tuple[str, typing.Any, str]]
) -> dash.html.Div:
    """
    Utility function constructs a grid layout html div of labeled argument elements
    :param label_element_widths: a list of label strings, content elements, and width specifications
    :return: A html Div containing the labels and elements in a grid
    """
    return dash.html.Div(
        [
            item
            for sublist in [
                [
                    dash.html.Div(label, style={"grid-area": str(index + 1) + " / 1"}),
                    dash.html.Div(
                        element,
                        style={"grid-area": str(index + 1) + " / 2", "width": width},
                    ),
                ]
                for index, (label, element, width) in enumerate(label_element_widths)
            ]
            for item in sublist
        ],
        style={
            "display": "grid",
            "grid-template-columns": "auto auto",
            "gap": "10px",
            "justifyContent": "start",
        },
    )


def even_grid_from_nested_elements(
    elements: typing.List[typing.List[typing.Any]],
) -> dash.html.Div:
    """
    Utility function constructs a grid layout html div from a nested list
    :param elements: a list of lists of Dash elements
    :return: A html Div containing the elements in a grid
    """
    return dash.html.Div(
        [
            item
            for sublist in [
                [
                    dash.html.Div(
                        element,
                        style={
                            "grid-area": str(column_index + 1)
                            + " / "
                            + str(row_index + 1)
                        },
                    )
                    for column_index, element in enumerate(row_elements)
                ]
                for row_index, row_elements in enumerate(elements)
            ]
            for item in sublist
        ],
        style={
            "display": "grid",
            "grid-template-columns": "auto auto",
            "gap": "10px",
            "justifyContent": "start",
        },
    )
