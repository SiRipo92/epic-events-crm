"""
Role ORM model.

Represents a department-level role within Epic Events.
Roles are stored as a separate table per school requirement —
never hardcoded as an enum column on the Collaborator table.

Seed data (inserted in base migration):
    id=1  name="MANAGEMENT"
    id=2  name="COMMERCIAL"
    id=3  name="SUPPORT"
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Role(Base):
    """ORM model for collaborator roles."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    collaborators: Mapped[list["Collaborator"]] = relationship(  # noqa: F821
        back_populates="role"
    )

    def __str__(self) -> str:
        """Return the role name as its string representation."""
        return self.name
