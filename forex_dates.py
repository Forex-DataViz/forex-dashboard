"""Resolve the latest published forex date, including weekends and holidays."""

from datetime import date, timedelta

import requests


def get_latest_date(today=None):
    today = today if today is not None else date.today()
    for days_back in range(5):
        requested_date = today - timedelta(days=days_back)
        url = (
            f"https://api.frankfurter.app/{requested_date.isoformat()}"
            "?from=USD&to=PHP"
        )
        response = requests.get(url).json()
        rates = response.get("rates", {})
        if not isinstance(rates, dict) or rates.get("PHP") is None:
            continue
        try:
            published_date = date.fromisoformat(response.get("date"))
        except (TypeError, ValueError):
            continue
        if published_date > requested_date:
            continue
        # A weekend/holiday request can return the preceding trading day's rate.
        # The time-series DataFrame contains that published date, not today's date.
        return published_date.isoformat()
    return None
