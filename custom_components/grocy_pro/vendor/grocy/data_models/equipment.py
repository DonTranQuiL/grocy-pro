from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Equipment(BaseModel):
    """A piece of tracked equipment."""

    id: int
    name: str | None = None
    description: str | None = None
    instruction_manual_file_name: str | None = None
    created_timestamp: datetime | None = None
    userfields: dict | None = None

    @classmethod
    def from_equipment_data(cls, data) -> Equipment:
        """Create from an equipment data object."""
        return cls(
            id=data.id,
            name=data.name,
            description=data.description,
            instruction_manual_file_name=data.instruction_manual_file_name,
            created_timestamp=data.created_timestamp,
            userfields=data.userfields,
        )

    @classmethod
    def from_details_response(cls, resp) -> Equipment:
        """Create from an equipment-details API response."""
        return cls.from_equipment_data(resp.equipment)

    @classmethod
    def from_dict(cls, data: dict) -> Equipment:
        """Create from a raw dictionary."""
        return cls(
            id=data.get("id"),
            name=data.get("name"),
            description=data.get("description"),
            instruction_manual_file_name=data.get("instruction_manual_file_name"),
            created_timestamp=data.get("row_created_timestamp")
            or data.get("created_timestamp"),
            userfields=data.get("userfields"),
        )

    def get_details(self, api_client):
        """Fetch and populate full equipment details from the API."""
        details = api_client.get_equipment(self.id)
        if details:
            updated = Equipment.from_details_response(details)
            self.__dict__.update(updated.__dict__)

    def as_dict(self):
        """Convert to a plain dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "instruction_manual_file_name": self.instruction_manual_file_name,
            "created_timestamp": self.created_timestamp,
            "userfields": self.userfields,
        }
