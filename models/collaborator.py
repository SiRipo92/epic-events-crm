"""
Collaborator ORM model.

Represents an internal Epic Events staff member. Every user of the
CRM is a Collaborator with one of three roles: MANAGEMENT, COMMERCIAL,
or SUPPORT. Authentication and role enforcement are built on top of
this model.

Deletion policy:
    Collaborators are never hard-deleted. When a staff member leaves,
    is_active is set to False by the service layer after confirming
    all clients, contracts, and events have been reassigned. This
    preserves historical records and prevents orphaned data.
"""

import bcrypt
from datetime import datetime
from sqlalchemy import String, Enum as SAEnum, DateTime, Boolean, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from permissions.roles import RoleEnum


class Collaborator(Base):
    """ORM model for the collaborators table.

    A collaborator is any staff member who can log into the CRM.
    Their role determines which commands they can execute and which
    data they can read or modify. Inactive collaborators cannot log in
    but their historical records are preserved.

    Attributes:
        is_active: Soft-delete flag. False means the collaborator has
                   left the company. The service layer enforces that
                   all clients, contracts, and events are reassigned
                   before this flag can be set to False.

    Relationships:
        clients: All clients this collaborator manages (Commercial role).
        contracts: All contracts this collaborator is responsible for.
        events: All events this collaborator is assigned to support.
    """

    __tablename__ = "collaborators"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[RoleEnum] = mapped_column(SAEnum(RoleEnum), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=func.now()
    )

    clients: Mapped[list["Client"]] = relationship(back_populates="commercial")
    contracts: Mapped[list["Contract"]] = relationship(
        back_populates="commercial",
        foreign_keys="[Contract.commercial_id]"
    )
    events: Mapped[list["Event"]] = relationship(back_populates="support")

    @property
    def full_name(self) -> str:
        """Return the collaborator's full name in display format."""
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name_formal(self) -> str:
        """Return the name in formal format: LAST NAME, First name."""
        return f"{self.last_name.upper()}, {self.first_name}"

    @property
    def is_manager(self) -> bool:
        """Return True if this collaborator has the MANAGEMENT role.

        Returns:
            bool: True if role is MANAGEMENT.
        """
        return self.role == RoleEnum.MANAGEMENT

    @property
    def is_commercial(self) -> bool:
        """Return True if this collaborator has the COMMERCIAL role.

        Returns:
            bool: True if role is COMMERCIAL.
        """
        return self.role == RoleEnum.COMMERCIAL

    @property
    def is_support(self) -> bool:
        """Return True if this collaborator has the SUPPORT role.

        Returns:
            bool: True if role is SUPPORT.
        """
        return self.role == RoleEnum.SUPPORT

    def set_password(self, plain_text: str) -> None:
        """Hash and store the password using bcrypt.

        Uses a cost factor of 12 for brute-force resistance.
        The plain text password is never stored.

        Args:
            plain_text: The raw password string to hash.
        """
        self.password_hash = bcrypt.hashpw(
            plain_text.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

    def verify_password(self, plain_text: str) -> bool:
        """Verify a plain text password against the stored hash.

        Uses bcrypt.checkpw which is timing-safe against
        brute-force and timing attacks.

        Args:
            plain_text: The raw password string to verify.

        Returns:
            bool: True if the password matches the stored hash.
        """
        return bcrypt.checkpw(
            plain_text.encode("utf-8"),
            self.password_hash.encode("utf-8")
        )
