import unittest
from eu5_mcp import values_at, get_player_country, extract_player_economy


class PathTests(unittest.TestCase):
    def test_nested(self):
        self.assertEqual(values_at({"a": [{"b": 3}]}, "a.0.b"), 3)

    def test_missing(self):
        self.assertIsNone(values_at({"a": []}, "a.0.b"))

    def test_bad_type(self):
        self.assertIsNone(values_at({"a": "hi"}, "a.b"))

    def test_player_economy(self):
        data = {"metadata": {"date": "1341.1.21", "version": "1.4.5", "player_country_name": "Osmanlı"},
                "played_country": {"country": 41}, "countries": {"database": {"41": {
                    "definition": "TUR", "currency_data": {"gold": 192.1},
                    "owned_locations": [1, 2], "economy": {"income": 16.57, "expense": 17.24,
                    "recent_balance": [1, 2, 3]}}}}}
        self.assertEqual(get_player_country(data)[0], "41")
        result = extract_player_economy(data)
        self.assertAlmostEqual(result["monthly_balance"], -0.67)
        self.assertEqual(result["owned_locations"], 2)

    def test_missing_country(self):
        with self.assertRaises(ValueError):
            get_player_country({"played_country": {"country": 41}, "countries": {"database": {}}})


if __name__ == "__main__":
    unittest.main()
