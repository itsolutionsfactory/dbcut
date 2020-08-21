import unittest
from collections import OrderedDict

from dbcut.utils import sorted_nested_dict


def test_simple_dict_is_sorted():
    data = {
        "c": 1,
        "a": 2,
        "b": 3,
    }
    expected = OrderedDict([("a", 2), ("b", 3), ("c", 1)])
    assert expected == sorted_nested_dict(data)


def test_nested_iterables_are_sorted():
    data = {
        "c": [1, 3, 2],
        "a": 2,
        "b": (3, 1, 2),
    }
    expected = OrderedDict(
        [
            ("a", 2),
            # The tuple is transformed into a list here. Still an iterable though.
            ("b", [1, 2, 3]),
            ("c", [1, 2, 3]),
        ]
    )
    assert expected == sorted_nested_dict(data)


def test_nested_dicts_are_sorted():
    data = {
        "c": 1,
        "a": {"b": 1, "a": 2},
        "b": 3,
    }
    expected = OrderedDict(
        [("a", OrderedDict([("a", 2), ("b", 1)])), ("b", 3), ("c", 1)]
    )
    assert expected == sorted_nested_dict(data)


def test_non_dicts_are_untouched():
    data = "ravioli"
    assert data is sorted_nested_dict(data)
    data = ["r", "a", "v", "i", "o", "l", "i"]
    assert data is sorted_nested_dict(data)
    data = 42
    assert data is sorted_nested_dict(data)

    class Custom:
        pass

    data = Custom()
    assert data is sorted_nested_dict(data)
