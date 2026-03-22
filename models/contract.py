"""
Contract ORM model.

Represents a formal agreement between Epic Events and a client.
A contract must reach SIGNED status before an event can be created
against it. Tracks both the total agreed amount and the remaining
unpaid amount.

Deletion policy:
    Contracts are never hard-deleted — they are legal and financial
    records. A contract is cancelled via status=CANCELLED.
    The service layer also cancels the linked event when a contract
    is cancelled. client_id is nullable to support RGPD client
    deletion while retaining the financial record.
"""

from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, Enum as SAEnum, func, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base
from permissions.roles import ContractStatus


class Contract(Base):
    """ORM model for the contracts table.

    Contracts are created by Management and linked to both a client
    and the commercial collaborator responsible for that client.
    The status field drives the full contract lifecycle and gates
    event creation — only SIGNED or COMPLETED contracts can have
    events created against them.

    Financial amounts use Decimal (mapped to Numeric) rather than float
    to avoid binary floating point rounding errors in monetary values.

    Attributes:
        client_id: Nullable FK. Set to NULL if the client is deleted
                   under RGPD. The contract record is retained.
        status: Drives the contract lifecycle. See ContractStatus for
                valid states and transitions.

    Computed properties:
        is_signed: True if status is SIGNED or COMPLETED.
        is_cancelled: True if status is CANCELLED.

    Relationships:
        client: The Client this contract belongs to (nullable after
                RGPD client deletion).
        commercial: The Collaborator responsible for this contract.
        event: The single Event generated from this contract (nullable).
    """

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"), nullable=True
    )
    commercial_id: Mapped[int] = mapped_column(
        ForeignKey("collaborators.id"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    status: Mapped[ContractStatus] = mapped_column(
        SAEnum(ContractStatus),
        default=ContractStatus.DRAFT,
        server_default="DRAFT",
        nullable=False
    )

    client: Mapped["Client | None"] = relationship(
        back_populates="contracts",
        passive_deletes=True
    )
    commercial: Mapped["Collaborator"] = relationship(
        back_populates="contracts",
        foreign_keys="[Contract.commercial_id]"
    )
    event: Mapped["Event | None"] = relationship(
        back_populates="contract",
        uselist=False
    )

    @property
    def is_signed(self) -> bool:
        """Return True if the contract has been signed.

        A contract is considered signed if its status is SIGNED
        or COMPLETED — both represent post-signature states.

        Returns:
            bool: True if status is SIGNED or COMPLETED.
        """
        return self.status in (ContractStatus.SIGNED, ContractStatus.COMPLETED)

    @property
    def is_cancelled(self) -> bool:
        """Return True if the contract has been cancelled.

        Returns:
            bool: True if status is CANCELLED.
        """
        return self.status == ContractStatus.CANCELLED

    def is_fully_paid(self) -> bool:
        """Return True if there is no remaining amount owed on this contract.

        Returns:
            bool: True if remaining_amount is zero or less, False otherwise.
        """
        return self.remaining_amount <= Decimal("0")
