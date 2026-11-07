from datetime import date
import unittest
from unittest.mock import Mock, patch

from forex_dates import get_latest_date


class LatestForexDateTests(unittest.TestCase):
    @patch("forex_dates.requests.get")
    def test_weekend_uses_fridays_published_date(self, get):
        get.return_value.json.return_value = {
            "date": "2026-11-06", "rates": {"PHP": 63.017},
        }
        for today in (date(2026, 11, 7), date(2026, 11, 8)):
            with self.subTest(today=today):
                get.reset_mock()
                self.assertEqual(get_latest_date(today), "2026-11-06")
                get.assert_called_once_with(
                    f"https://api.frankfurter.app/{today.isoformat()}?from=USD&to=PHP"
                )

    @patch("forex_dates.requests.get")
    def test_weekday_uses_same_day_when_published(self, get):
        get.return_value.json.return_value = {
            "date": "2026-11-06", "rates": {"PHP": 63.017},
        }
        self.assertEqual(get_latest_date(date(2026, 11, 6)), "2026-11-06")

    @patch("forex_dates.requests.get")
    def test_holiday_or_before_publication_uses_prior_business_day(self, get):
        get.return_value.json.return_value = {
            "date": "2026-11-06", "rates": {"PHP": 63.017},
        }
        self.assertEqual(get_latest_date(date(2026, 11, 9)), "2026-11-06")

    @patch("forex_dates.requests.get")
    def test_invalid_response_falls_back_to_previous_requested_day(self, get):
        invalid_responses = [
            {}, {"rates": {"PHP": 63.017}},
            {"date": "not-a-date", "rates": {"PHP": 63.017}},
            {"date": "2026-11-08", "rates": {"PHP": 63.017}},
            {"date": "2026-11-06", "rates": {}},
            {"date": "2026-11-06", "rates": {"PHP": None}},
        ]
        for response in invalid_responses:
            with self.subTest(response=response):
                get.reset_mock()
                get.side_effect = [
                    Mock(json=Mock(return_value=response)),
                    Mock(json=Mock(return_value={
                        "date": "2026-11-06", "rates": {"PHP": 63.017},
                    })),
                ]
                self.assertEqual(get_latest_date(date(2026, 11, 7)), "2026-11-06")
                self.assertEqual(get.call_count, 2)

    @patch("forex_dates.requests.get")
    def test_no_published_date_after_five_attempts_returns_none(self, get):
        get.return_value.json.return_value = {"rates": {"PHP": 63.017}}
        self.assertIsNone(get_latest_date(date(2026, 11, 7)))
        self.assertEqual(get.call_count, 5)


if __name__ == "__main__":
    unittest.main()
