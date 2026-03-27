"""ORM model for the collaborators table.

Represents a user in the Epic Events system with a specific role.
Collaborators log in via JWT and perform actions based on their role.
"""

from enum import Enum

from sqlalchemy import String, Boolean
from sqlalchemy.orm import mapped_column, relationship

from models.base import Base


class Role(str, Enum):
    """Available roles in the Epic Events CRM."""
    MANAGEMENT = "MANAGEMENT"
    COMMERCIAL = "COMMERCIAL"
    SUPPORT = "SUPPORT"


class Collaborator(Base):
    """ORM model for the collaborators table.

    A collaborator is a system user identified by email and password.
    Each collaborator has a role (MANAGEMENT, COMMERCIAL, SUPPORT) that
    determines their permissions throughout the CRM.

    Attributes:
        id: Primary key.
        first_name: Collaborator's first name.
        last_name: Collaborator's last name.
        email: Unique email used for authentication.
        password_hash: Bcrypt hash of the collaborator's password.
        role: The collaborator's role (MANAGEMENT, COMMERCIAL, SUPPORT).
        is_active: Whether the collaborator can log in. Set to False on deactivation.

    Relationships:
        clients: Clients owned by this collaborator (commercial_id).
        contracts: Contracts managed by this collaborator (commercial_id).
        events: Events supported by this collaborator (support_id).
    """

    __tablename__ = "collaborators"

    id: mapped_column[int] = mapped_column(primary_key=True)
    first_name: mapped_column[str] = mapped_column(String(50), nullable=False)
    last_name: mapped_column[str] = mapped_column(String(50), nullable=False)
    email: mapped_column[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: mapped_column[str] = mapped_column(String(255), nullable=False)
    role: mapped_column[Role] = mapped_column(String(20), nullable=False)
    is_active: mapped_column[bool] = mapped_column(Boolean, default=True, nullable=False)

    clients: relationship = relationship(
        "Client",
        back_populates="commercial",
        foreign_keys="Client.commercial_id",
    )
    contracts: relationship = relationship(
        "Contract",
        back_populates="commercial",
        foreign_keys="Contract.commercial_id",
    )
    events: relationship = relationship(
        "Event",
        back_populates="support",
        foreign_keys="Event.support_id",
    )

    @property
    def full_name(self) -> str:
        """Return the collaborator's full name in display format."""
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name_formal(self) -> str:
        """Return the collaborator's name in formal format: LASTNAME, First name."""
        return f"{self.last_name.upper()}, {self.first_name}"

    def __repr__(self) -> str:
        return f"<Collaborator(id={self.id}, email={self.email!r}, role={self.role.value})>"
