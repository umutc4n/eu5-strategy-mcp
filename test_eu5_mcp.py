import unittest
from eu5_mcp import values_at


class PathTests(unittest.TestCase):
    def test_nested(self):
        self.assertEqual(values_at({"a": [{"b": 3}]}, "a.0.b"), 3)

    def test_missing(self):
        self.assertIsNone(values_at({"a": []}, "a.0.b"))

    def test_bad_type(self):
        self.assertIsNone(values_at({"a": "hi"}, "a.b"))


if __name__ == "__main__":
    unittest.main()
