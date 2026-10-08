"""fetch_grocy_data against the recorded demo data."""

from __future__ import annotations

from datetime import UTC

from grocy import Grocy

from custom_components.grocy_pro.const import FEATURE_ENTITIES
from custom_components.grocy_pro.grocy_data import _is_past, fetch_grocy_data
from custom_components.grocy_pro.helpers import as_attribute

ALL_KEYS = [key for keys in FEATURE_ENTITIES.values() for key in keys]


def _api() -> Grocy:
    return Grocy("http://grocy.local", "key", port=9192)


def test_fetch_all(grocy_server, frozen) -> None:
    """Every bucket is filled and JSON serialisable."""
    data = fetch_grocy_data(_api(), ALL_KEYS)
    counts = {key: len(value) for key, value in data.items()}
    assert counts == {
        "stock": 22,
        "expiring_products": 5,
        "overdue_products": 1,
        "expired_products": 0,
        "missing_products": 2,
        "shopping_list": 2,
        "tasks": 5,
        "overdue_tasks": 2,
        "chores": 6,
        "overdue_chores": 0,
        "meal_plan": 5,
        "batteries": 4,
        "overdue_batteries": 1,
    }
    import json

    for value in data.values():
        json.dumps([as_attribute(item) for item in value])


def test_one_volatile_call(grocy_server, frozen) -> None:
    """The four product buckets come from a single /stock/volatile request."""
    fetch_grocy_data(_api(), ALL_KEYS)
    paths = [path for _, path, _ in grocy_server.calls]
    assert paths.count("stock/volatile") == 1
    assert paths.count("objects/products") == 1


def test_fetch_subset(grocy_server, frozen) -> None:
    """Only requested keys are fetched and returned."""
    data = fetch_grocy_data(_api(), ["tasks"])
    assert set(data) == {"tasks"}
    assert {path for _, path, _ in grocy_server.calls} == {"tasks"}


def test_meal_plan_sorted_and_filtered(grocy_server, frozen) -> None:
    """Meal plan items are sorted by day and the request filters past days."""
    data = fetch_grocy_data(_api(), ["meal_plan"])
    days = [item.meal_plan.day for item in data["meal_plan"]]
    assert days == sorted(days)


def test_is_past() -> None:
    """Dates, datetimes and None."""
    from datetime import date, datetime, timedelta

    now = datetime(2026, 10, 8, 12, 0)
    assert _is_past(None, now) is False
    assert _is_past(date(2026, 10, 7), now) is True
    assert _is_past(date(2026, 10, 8), now) is False
    assert _is_past(datetime(2026, 10, 8, 11, 0), now) is True
    assert _is_past(datetime(2026, 10, 8, 13, 0), now) is False
    aware = datetime(2026, 10, 8, 13, 0).astimezone() - timedelta(hours=2)
    assert _is_past(aware, now) is True
    assert _is_past(datetime(2030, 1, 1, tzinfo=UTC), now) is False
    assert _is_past("2026-01-01", now) is False
