"""The Grocy calendar."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from http import HTTPStatus

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.grocy_pro.calendar import parse_ical

from .conftest import FIXTURE

ICAL = FIXTURE["calendar/ical"]["text"]


def test_parse_demo_feed() -> None:
    """All events of the demo feed are parsed and sorted."""
    events = parse_ical(ICAL)
    assert len(events) == 48
    starts = [e.start_datetime_local for e in events]
    assert starts == sorted(starts)
    day_events = [e for e in events if not isinstance(e.start, datetime)]
    assert day_events
    assert all(e.end == e.start + timedelta(days=1) for e in day_events)
    timed = [e for e in events if isinstance(e.start, datetime)]
    assert timed
    assert all(e.end > e.start for e in timed)
    battery = next(
        e for e in timed if e.summary == "Battery charge cycle due: Battery1"
    )
    # 2026-10-08 23:59:59 Europe/Berlin
    assert battery.start.astimezone(dt_util.UTC) == datetime(
        2026, 10, 8, 21, 59, 59, tzinfo=dt_util.UTC
    )


def test_utc_and_naive_times_are_wall_clock(hass: HomeAssistant) -> None:
    """A Grocy server in UTC labels local wall-clock times as UTC."""
    text = (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:Grocy\r\n"
        "BEGIN:VEVENT\r\nUID:a\r\nSUMMARY:Chore due: Water plants\r\n"
        "DTSTART:20261008T180000Z\r\nDTEND:20261008T180000Z\r\nEND:VEVENT\r\n"
        "BEGIN:VEVENT\r\nUID:b\r\nSUMMARY:Task due: Naive\r\n"
        "DTSTART:20261008T070000\r\nEND:VEVENT\r\n"
        "BEGIN:VEVENT\r\nUID:c\r\nSUMMARY:Meal plan: Pizza\r\n"
        "DTSTART;VALUE=DATE:20261009\r\nDTEND;VALUE=DATE:20261011\r\nEND:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    events = {e.uid: e for e in parse_ical(text)}
    tz = dt_util.get_default_time_zone()
    assert events["a"].start == datetime(2026, 10, 8, 18, 0, tzinfo=tz)
    assert events["a"].end - events["a"].start == timedelta(minutes=1)
    assert events["b"].start == datetime(2026, 10, 8, 7, 0, tzinfo=tz)
    assert events["c"].start == date(2026, 10, 9)
    assert events["c"].end == date(2026, 10, 11)


async def test_calendar_entity(
    hass: HomeAssistant, setup_integration, hass_client, grocy_server
) -> None:
    """The calendar entity serves events and caches the feed."""
    await setup_integration()
    state = hass.states.get("calendar.grocy_calendar")
    assert state is not None
    assert state.attributes["message"]

    client = await hass_client()
    response = await client.get(
        "/api/calendars/calendar.grocy_calendar"
        "?start=2026-10-01T00:00:00Z&end=2026-10-15T00:00:00Z"
    )
    assert response.status == HTTPStatus.OK
    events = await response.json()
    assert events
    assert all(e["summary"] for e in events)

    fetches = [p for _, p, _ in grocy_server.calls if p == "calendar/ical"]
    assert len(fetches) == 1


async def test_calendar_survives_errors(
    hass: HomeAssistant, setup_integration, grocy_server, frozen
) -> None:
    """A failing feed keeps the old events."""
    entry = await setup_integration()
    entity = hass.data["entity_components"]["calendar"].get_entity(
        "calendar.grocy_calendar"
    )
    count = len(entity._events)
    grocy_server.fail = 500
    frozen.tick(timedelta(minutes=16))
    await entity.async_update()
    assert len(entity._events) == count
    assert entry.runtime_data is not None
