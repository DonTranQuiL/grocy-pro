from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Battery(BaseModel):
    """A tracked battery with charge cycle history."""

    id: int
    name: str | None = None
    description: str | None = None
    used_in: str | None = None
    charge_interval_days: int | None = None
    created_timestamp: datetime | None = None
    charge_cycles_count: int | None = None
    userfields: dict | None = None
    last_charged: datetime | None = None
    last_tracked_time: datetime | None = None
    next_estimated_charge_time: datetime | None = None

    @classmethod
    def from_current_response(cls, resp) -> Battery:
        """Create from a current-batteries API response."""
        return cls(
            id=resp.id,
            last_tracked_time=resp.last_tracked_time,
            next_estimated_charge_time=resp.next_estimated_charge_time,
        )

    @classmethod
    def from_details_response(cls, resp) -> Battery:
        """Create from a battery-details API response."""
        return cls(
            id=resp.battery.id,
            name=resp.battery.name,
            description=resp.battery.description,
            used_in=resp.battery.used_in,
            charge_interval_days=resp.battery.charge_interval_days,
            created_timestamp=resp.battery.created_timestamp,
            userfields=resp.battery.userfields,
            charge_cycles_count=resp.charge_cycles_count,
            last_charged=resp.last_charged,
            last_tracked_time=resp.last_charged,
            next_estimated_charge_time=resp.next_estimated_charge_time,
        )

    def get_details(self, api_client):
        """Fetch and populate full battery details from the API."""
        details = api_client.get_battery(self.id)
        if details:
            updated = Battery.from_details_response(details)
            self.__dict__.update(updated.__dict__)
