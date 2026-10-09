from pydantic import BaseModel


class User(BaseModel):
    """A Grocy user account."""

    id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
