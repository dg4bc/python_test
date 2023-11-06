"""A utility for combining unstructured sorted entry and exit sequences into entry exit pairs"""

import typing


def generate_trade_sequence(
    entries: typing.List[int], exits: typing.List[int]
) -> typing.List[typing.Tuple[int, int]]:
    """
    Takes entry and exit signals and converts them to a sequence of matched pairs
    :param entries: Sorted references where a trade should be entered
    :param exits: Sorted references where a trade should be existed
    :return: Pairs of non-intersecting entry and exit references
    """
    last_entry = entry_index = exit_index = 0
    pairs: typing.List[typing.Tuple[int, int]] = []
    in_trade: bool = False
    while entry_index < len(entries) or exit_index < len(exits):
        if entry_index >= len(entries) or (
            exit_index < len(exits) and exits[exit_index] < entries[entry_index]
        ):
            if in_trade:
                pairs.append((last_entry, exits[exit_index]))
                in_trade = False
            exit_index += 1
        else:
            if not in_trade:
                last_entry = entries[entry_index]
                in_trade = True
            entry_index += 1
    return pairs
