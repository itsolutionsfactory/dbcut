import unittest
from collections import OrderedDict

from dbcut.utils import sorted_nested_dict


class SortedNestedDictTestCase(unittest.TestCase):
    def test_simple_dict_is_sorted(self):
        data = {
            "c": 1,
            "a": 2,
            "b": 3,
        }
        expected = OrderedDict([("a", 2), ("b", 3), ("c", 1)])
        self.assertEqual(expected, sorted_nested_dict(data))

    def test_nested_iterables_are_sorted(self):
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
        self.assertEqual(expected, sorted_nested_dict(data))

    def test_nested_dicts_are_sorted(self):
        data = {
            "c": 1,
            "a": {"b": 1, "a": 2},
            "b": 3,
        }
        expected = OrderedDict(
            [("a", OrderedDict([("a", 2), ("b", 1)])), ("b", 3), ("c", 1)]
        )
        self.assertEqual(expected, sorted_nested_dict(data))

    def test_non_dicts_are_untouched(self):
        data = "ravioli"
        self.assertIs(data, sorted_nested_dict(data))
        data = ["r", "a", "v", "i", "o", "l", "i"]
        self.assertIs(data, sorted_nested_dict(data))
        data = 42
        self.assertIs(data, sorted_nested_dict(data))

        class Custom:
            pass

        data = Custom()
        self.assertIs(data, sorted_nested_dict(data))


if __name__ == "__main__":
    unittest.main()
