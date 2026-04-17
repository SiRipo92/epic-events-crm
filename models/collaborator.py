"""
Collaborator ORM model.

Represents an internal Epic Events employee. All system access is tied
to a Collaborator account. Authentication is handled via bcrypt password
hashing and JWT session tokens.

Deletion policy:
    Collaborators are never hard-deleted. Deactivation sets is_active = False
    and revokes session access. All dossiers must be reassigned before
    deactivation can complete.
"""

from datetime import datetime

import bcrypt
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Collaborator(Base):
    """
    ORM model for the collaborators table.

    Attributes:
        employee_number: Human-readable unique identifier e.g. EMP-001.
                         Distinct from the database primary key id.
        role_id:         FK → Role. Role is a separate table per school
                         requirement — never hardcoded as an enum column.
        password_hash:   bcrypt hash. Never stored as plaintext.
        is_active:       False blocks login. Set to False on deactivation.
        must_change_password: True forces password change on next login.
                              Set to True on account creation.

    Relationships:
        role:     The Role assigned to this collaborator.
        clients:  Clients this collaborator owns (Commercial role).
        contracts: Contracts this collaborator is assigned to.
        events:   Events this collaborator is assigned to support.
    """

    __tablename__ = "collaborators"
    __table_args__ = (
        CheckConstraint(
            "employee_number ~ '^EMP-[0-9]{3}$'",
            name="ck_collaborator_employee_number_format",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )

    # ── Relationships ──────────────────────────────────────────────────────────
    role: Mapped["Role"] = relationship(back_populates="collaborators")  # noqa: F821

    # ── Computed properties ────────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        """Return the collaborator's full name."""
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name_formal(self) -> str:
        """Return the collaborator's name in formal format."""
        return f"{self.last_name.upper()}, {self.first_name}"

    @property
    def is_manager(self) -> bool:
        """Return True if this collaborator has the MANAGEMENT role."""
        return self.role.name == "MANAGEMENT"

    @property
    def is_commercial(self) -> bool:
        """Return True if this collaborator has the COMMERCIAL role."""
        return self.role.name == "COMMERCIAL"

    @property
    def is_support(self) -> bool:
        """Return True if this collaborator has the SUPPORT role."""
        return self.role.name == "SUPPORT"

    def set_password(self, plain_text: str) -> None:
        """Hash and store a plaintext password using bcrypt.

        Args:
            plain_text: The raw password string to hash.
        """
        self.password_hash = bcrypt.hashpw(
            plain_text.encode("utf-8"), bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

    def verify_password(self, plain_text: str) -> bool:
        """Verify a plaintext password against the stored hash.

        Args:
            plain_text: The raw password to verify.

        Returns:
            bool: True if the password matches the stored hash.
        """
        return bcrypt.checkpw(
            plain_text.encode("utf-8"), self.password_hash.encode("utf-8")
        )
