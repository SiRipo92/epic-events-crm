"""
Client ORM model.

Represents an external client of Epic Events — a company or individual
who organises events through the agency. Each client is owned by exactly
one Commercial collaborator who created their profile and tracks their
lifecycle from initial prospect through to completed dossier.

Deletion policy:
    Clients can be hard-deleted (e.g. RGPD right to erasure). When a
    client is deleted, their contracts are retained for business and
    accounting records but client_id on those contracts is set to NULL.
    This preserves financial history while removing personal data.
    Before deletion the client status should be set to INACTIVE.
"""

from datetime import datetime
from sqlalchemy import String, DateTime, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
import enum


class ClientStatus(str, enum.Enum):
    PROSPECT = "prospect"
    IN_NEGOTIATION = "in_negotiation"
    PENDING_SIGNATURE = "pending_signature"
    ACTIVE = "active"
    IN_SUPPORT = "in_support"
    COMPLETED = "completed"
    INACTIVE = "inactive"


class Client(Base):
    """ORM model for the clients table.

    A client is created by a Commercial collaborator and remains
    assigned to that collaborator via commercial_id. Only the owning
    commercial can update a client's profile.

    The status field tracks the full client lifecycle, from initial
    prospect through to completed dossier or inactive. This drives
    Management's assignment workflow — showing which clients need a
    commercial rep, which need support assigned, and which are closed.

    Timestamps:
        created_at: Set automatically on insert via the database server.
        updated_at: Null until the first update occurs. Set automatically
                    on each subsequent modification.

    Relationships:
        commercial: The Collaborator responsible for this client.
        contracts: All contracts associated with this client. When the
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=func.now()
    )

    # To update later
    commercial_id: Mapped[int] = mapped_column(nullable=False)

    status: Mapped[ClientStatus] = mapped_column(
        SAEnum(ClientStatus),
        default=ClientStatus.PROSPECT,
        server_default="PROSPECT",
        nullable=False
    )


    contracts: Mapped[list["Contract"]] = relationship(
        back_populates="client",
        passive_deletes=True
    )

    @property
    def full_name(self) -> str:
        """Return the client's full name in display format.

        Returns:
            str: First name followed by last name.
        """
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name_formal(self) -> str:
        """Return the client's name in formal format: LAST NAME, First name.

        Returns:
            str: Last name in uppercase followed by first name.
        """
        return f"{self.last_name.upper()}, {self.first_name}"

    @property
    def has_active_support(self) -> bool:
        """Return True if any of this client's events have a support member assigned.

        Traverses the client → contracts → event chain to check whether
        a support collaborator is assigned to any active event. Always
        reflects current data state — never stored as a column.

        Returns:
            bool: True if at least one event has support_id set.
        """
        return any(
            event.support_id is not None
            for contract in self.contracts
            for event in ([] if contract.event is None else [contract.event])
        )
