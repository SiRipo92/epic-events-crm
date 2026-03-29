"""
Contract ORM model.

Represents a formal agreement between Epic Events and a client.
A contract must reach DEPOSIT_RECEIVED status before an event can be
created against it. Tracks both the total agreed amount and the
remaining unpaid balance.

Status lifecycle:
    DRAFT → PENDING → SIGNED → DEPOSIT_RECEIVED → PAID_IN_FULL
    Any active state → CANCELLED (terminal)

Deletion policy:
    Contracts are never hard-deleted — they are legal and financial
    records. A contract is closed via status=CANCELLED.
    The service layer also cancels the linked event when a contract
    is cancelled. client_id is nullable to support RGPD client
    deletion while retaining the financial record.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, false, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base


class ContractStatus(str, enum.Enum):
    """Lifecycle states for a contract.

    Transitions are enforced by the service layer — the model itself
    does not validate state machine progression.

    DRAFT:            Contract created by Management. Editable.
    PENDING:          Submitted to client for signature.
    SIGNED:           Client has signed. Awaiting deposit.
    DEPOSIT_RECEIVED: Deposit recorded. Event creation now unlocked.
    PAID_IN_FULL:     Final payment received. Dossier closed.
    CANCELLED:        Terminal state. No further transitions allowed.
    """

    DRAFT = "draft"
    PENDING = "pending"
    SIGNED = "signed"
    DEPOSIT_RECEIVED = "deposit_received"
    PAID_IN_FULL = "paid_in_full"
    CANCELLED = "cancelled"


class Contract(Base):
    """ORM model for the contracts table.

    Contracts are created by Management and linked to both a client
    and the commercial collaborator responsible for that client.
    The status field drives the full contract lifecycle and gates
    event creation — only DEPOSIT_RECEIVED contracts can have
    an event created against them.

    Financial amounts use Decimal (mapped to Numeric) rather than float
    to avoid binary floating-point rounding errors in monetary values.
    The remaining_amount field is never edited directly — it is reduced
    exclusively via the record_payment() service method.

    Attributes:
        client_id:         Nullable FK. Set to NULL if the client is
                           deleted under RGPD. The contract is retained.
        commercial_id:     FK to the Collaborator (Commercial role)
                           responsible for this contract. Populated as
                           a bare int for now — FK constraint added in
                           Epic 2 once the collaborators table is stable.
        deposit_received:  Set to True when Management records the
                           deposit. Triggers DEPOSIT_RECEIVED transition.
        total_amount:      The full agreed contract value.
        remaining_amount:  Starts equal to total_amount. Reduced by
                           recorded payments only. Reaches 0 on
                           PAID_IN_FULL.
        status:            Current lifecycle state. See ContractStatus.

    Computed properties:
        is_signed:           True if status is SIGNED or beyond
                             (but not CANCELLED).
        is_deposit_received: True if status is DEPOSIT_RECEIVED or
                             PAID_IN_FULL.
        is_fully_paid:       True if status is PAID_IN_FULL.
        is_cancelled:        True if status is CANCELLED.

    Relationships:
        client:     The Client this contract belongs to (nullable after
                    RGPD client deletion).
        commercial: The Collaborator responsible for this contract.
        event:      The single Event generated from this contract
                    (nullable — None until Commercial creates it).
    """

    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)

    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("clients.id", ondelete="SET NULL"),
        nullable=True,
    )

    # To update later: add ForeignKey("collaborators.id") in Epic 2
    commercial_id: Mapped[int] = mapped_column(nullable=False)

    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    remaining_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    deposit_received: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=false(),
        nullable=False,
    )

    status: Mapped[ContractStatus] = mapped_column(
        SAEnum(ContractStatus, name="contractstatus"),
        default=ContractStatus.DRAFT,
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

    client: Mapped["Client | None"] = relationship(  # noqa: F821
        back_populates="contracts",
        passive_deletes=True,
    )

    event: Mapped["Event | None"] = relationship(  # noqa: F821
        back_populates="contract",
        uselist=False,
    )

    # ── Computed properties ────────────────────────────────────────────────────

    @property
    def is_signed(self) -> bool:
        """Return True if the contract has been signed by the client.

        A contract is considered signed once it has moved past PENDING,
        as long as it has not been cancelled. Covers: SIGNED,
        DEPOSIT_RECEIVED, and PAID_IN_FULL.

        Returns:
            bool: True if status is SIGNED, DEPOSIT_RECEIVED, or
                  PAID_IN_FULL.
        """
        return self.status in (
            ContractStatus.SIGNED,
            ContractStatus.DEPOSIT_RECEIVED,
            ContractStatus.PAID_IN_FULL,
        )

    @property
    def is_deposit_received(self) -> bool:
        """Return True if a deposit has been recorded on this contract.

        Event creation is gated on this property — an event can only
        be created once the deposit is confirmed.

        Returns:
            bool: True if status is DEPOSIT_RECEIVED or PAID_IN_FULL.
        """
        return self.status in (
            ContractStatus.DEPOSIT_RECEIVED,
            ContractStatus.PAID_IN_FULL,
        )

    @property
    def is_fully_paid(self) -> bool:
        """Return True if the contract balance has been paid in full.

        Returns:
            bool: True if status is PAID_IN_FULL.
        """
        return self.status == ContractStatus.PAID_IN_FULL

    @property
    def is_cancelled(self) -> bool:
        """Return True if the contract has been cancelled.

        Returns:
            bool: True if status is CANCELLED.
        """
        return self.status == ContractStatus.CANCELLED
