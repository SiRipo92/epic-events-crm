"""
Client ORM model.

Represents an external client of Epic Events — a company or individual
who organises events through the agency. Each client is owned by exactly
one Commercial collaborator who created their profile.

Deletion policy:
    Clients can be hard-deleted (e.g. RGPD right to erasure). When a
    client is deleted, their contracts are retained for business and
    accounting records but client_id on those contracts is set to NULL.
    This preserves financial history while removing personal data.
"""

from datetime import datetime

from sqlalchemy import DateTime, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class Client(Base):
    """ORM model for the clients table.

    A client is created by a Commercial collaborator and remains
    assigned to that collaborator via commercial_id. Only the owning
    Commercial can update a client's profile.

    Client lifecycle is not stored as a column. All lifecycle queries
    (e.g. which clients need support assigned, which dossiers are closed)
    are derived from the state of their contracts and events at the
    service layer. This avoids synchronisation bugs between stored
    status and actual contract/event state.

    Timestamps:
        created_at: Set automatically on insert via the database server.
        updated_at: Null until the first update occurs. Set automatically
                    on each subsequent modification.

    Relationships:
        commercial: The Collaborator responsible for this client.
                    FK constraint added in Epic 2 once the collaborators
                    table is stable.
        contracts:  All contracts associated with this client. When the
                    client is deleted, contract.client_id is set to NULL
                    rather than cascading the deletion.
    """

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(150), nullable=True)

    commercial_id: Mapped[int] = mapped_column(
        ForeignKey("collaborators.id"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        onupdate=func.now(),
    )

    # ── Relationships ──────────────────────────────────────────────────────────

    contracts: Mapped[list["Contract"]] = relationship(  # noqa: F821
        back_populates="client",
        passive_deletes=True,
    )

    # ── Computed properties ────────────────────────────────────────────────────

    @property
    def full_name(self) -> str:
        """Return the client's full name in display format.

        Returns:
            str: First name followed by last name.
        """
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name_formal(self) -> str:
        """Return the client's name in formal format.

        Returns:
            str: Last name in uppercase followed by first name,
                 e.g. "DUPONT, Marie".
        """
        return f"{self.last_name.upper()}, {self.first_name}"

    @property
    def has_active_support(self) -> bool:
        """Return True if any of this client's events have a support member assigned.

        Traverses the client → contracts → event chain to check whether
        a support collaborator is currently assigned to any active event.
        Always reflects current data state — never stored as a column.

        Returns:
            bool: True if at least one event has support_id set.
        """
        return any(
            contract.event is not None and contract.event.support_id is not None
            for contract in self.contracts
        )
