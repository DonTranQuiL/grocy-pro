from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from .user import User


class TaskCategory(BaseModel):
    """A category for organizing tasks."""

    id: int
    name: str
    description: str | None = None
    row_created_timestamp: datetime | None = None


class Task(BaseModel):
    """A task with optional due date, category, and user assignment."""

    id: int
    name: str
    description: str | None = None
    due_date: datetime | None = None
    done: int = 0
    done_timestamp: datetime | None = None
    category_id: int | None = None
    category: TaskCategory | None = None
    assigned_to_user_id: int | None = None
    assigned_to_user: User | None = None
    userfields: dict | None = None

    @classmethod
    def from_response(cls, resp) -> Task:
        """Create from a task API response."""
        category = None
        if resp.category:
            category = TaskCategory(
                id=resp.category.id,
                name=resp.category.name,
                description=resp.category.description,
                row_created_timestamp=resp.category.row_created_timestamp,
            )
        assigned_user = None
        if resp.assigned_to_user:
            assigned_user = User(
                id=resp.assigned_to_user.id,
                username=resp.assigned_to_user.username,
                first_name=resp.assigned_to_user.first_name,
                last_name=resp.assigned_to_user.last_name,
                display_name=resp.assigned_to_user.display_name,
            )
        return cls(
            id=resp.id,
            name=resp.name,
            description=resp.description,
            due_date=resp.due_date,
            done=resp.done,
            done_timestamp=resp.done_timestamp,
            category_id=resp.category_id,
            category=category,
            assigned_to_user_id=resp.assigned_to_user_id,
            assigned_to_user=assigned_user,
            userfields=resp.userfields,
        )
