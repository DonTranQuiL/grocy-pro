"""Calendar platform for Grocy Pro, built from Grocy's iCal feed."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

import icalendar
from homeassistant.components.calendar import (
    CalendarEntity,
    CalendarEntityDescription,
    CalendarEvent,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CALENDAR_REFRESH_INTERVAL, LOGGER
from .coordinator import (
    GrocyAuthError,
    GrocyConfigEntry,
    GrocyConnectionError,
    GrocyDataUpdateCoordinator,
    call_grocy,
)
from .entity import GrocyEntity

PARALLEL_UPDATES = 1


def _to_local(value: datetime) -> datetime:
    """Return an aware local datetime.

    Grocy stores wall-clock times. When the server runs in UTC (common in
    containers), the feed labels those wall-clock times as UTC, so UTC and naive
    values are read as local time. Other zones are converted normally.
    """
    if value.tzinfo is None or value.utcoffset() == timedelta(0):
        return value.replace(tzinfo=dt_util.get_default_time_zone())
    return dt_util.as_local(value)


def parse_ical(text: str) -> list[CalendarEvent]:
    """Parse Grocy's iCal feed into calendar events, sorted by start."""
    events: list[CalendarEvent] = []
    calendar = icalendar.Calendar.from_ical(text)
    for component in calendar.walk("VEVENT"):
        start_prop = component.get("DTSTART")
        if start_prop is None:
            continue
        start: date | datetime = start_prop.dt
        end_prop = component.get("DTEND")
        end: date | datetime | None = end_prop.dt if end_prop is not None else None

        if isinstance(start, datetime):
            start = _to_local(start)
            end = _to_local(end) if isinstance(end, datetime) else None
            if end is None or end <= start:
                # Grocy uses zero-length time-point events; give them a minute.
                end = start + timedelta(minutes=1)
        else:
            if not isinstance(end, date) or isinstance(end, datetime) or end <= start:
                end = start + timedelta(days=1)

        events.append(
            CalendarEvent(
                start=start,
                end=end,
                summary=str(component.get("SUMMARY", "")),
                description=str(component.get("DESCRIPTION", "")) or None,
                uid=str(component.get("UID")) if component.get("UID") else None,
            )
        )
    events.sort(key=lambda event: event.start_datetime_local)
    return events


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrocyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Grocy calendar when the calendar feature is enabled."""
    coordinator = entry.runtime_data
    if "FEATURE_FLAG_CALENDAR" in coordinator.stats.feature_flags:
        async_add_entities([GrocyCalendarEntity(coordinator)], True)


class GrocyCalendarEntity(GrocyEntity, CalendarEntity):
    """Due products, tasks, chores, batteries and meal plans from Grocy."""

    _attr_should_poll = True

    def __init__(self, coordinator: GrocyDataUpdateCoordinator) -> None:
        """Initialise."""
        super().__init__(
            coordinator,
            CalendarEntityDescription(
                key="calendar", name="Calendar", icon="mdi:calendar"
            ),
        )
        self._events: list[CalendarEvent] = []
        self._fetched: datetime | None = None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """No list attributes for the calendar."""
        return None

    @property
    def event(self) -> CalendarEvent | None:
        """Return the current or next event."""
        now = dt_util.now()
        for event in self._events:
            if event.end_datetime_local > now:
                return event
        return None

    async def _async_refresh_events(self, force: bool = False) -> None:
        now = dt_util.utcnow()
        if (
            not force
            and self._fetched is not None
            and now - self._fetched < CALENDAR_REFRESH_INTERVAL
        ):
            return
        try:
            text = await self.hass.async_add_executor_job(
                call_grocy, self.coordinator.grocy_api.calendar.ical
            )
            self._events = await self.hass.async_add_executor_job(
                parse_ical, text or ""
            )
        except (GrocyAuthError, GrocyConnectionError, ValueError) as err:
            LOGGER.warning("Could not load the Grocy calendar: %s", err)
            return
        self._fetched = now

    async def async_update(self) -> None:
        """Refresh the cached events (polled by Home Assistant)."""
        await self._async_refresh_events()

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return events between start_date and end_date."""
        await self._async_refresh_events()
        start = start_date.astimezone(UTC)
        end = end_date.astimezone(UTC)
        return [
            event
            for event in self._events
            if event.end_datetime_local.astimezone(UTC) > start
            and event.start_datetime_local.astimezone(UTC) < end
        ]
