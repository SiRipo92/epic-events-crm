"""
Event ORM model.

Represents a live event organised by Epic Events for a client.
An event is always linked to a signed contract and optionally assigned
a Support collaborator responsible for its execution.

Deletion policy:
    Events are not hard-deleted. If a contract is cancelled, the
    service layer also sets the event's is_cancelled flag to True.
    support_id is nullable — events begin unassigned and are assigned
    later by Management.
"""

from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Integer, Text, DateTime, Boolean, false
from sqlalchemy.orm import Mapped, mapped_column, relationship
from models.base import Base


class Event(Base):
    """ORM model for the events table.

    Events are created by Commercial collaborators once a contract is
    signed. Management assigns a Support member to each event.
    Support members can update the details of events assigned to them.

    Attributes:
        support_id: Nullable FK. NULL means no support has been assigned
                    yet. Management assigns this after event creation.
        is_cancelled: Soft-cancel flag. Set to True when the linked
                      contract is cancelled or the event itself is
                      cancelled by Management.

    Relationships:
        contract: The Contract that generated this event.
        support: The Collaborator assigned to support this event
                 (nullable until assigned by Management).
    """

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("contracts.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attendees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    support_id: Mapped[int | None] = mapped_column(
        ForeignKey("collaborators.id"), nullable=True
    )
    is_cancelled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )

    contract: Mapped["Contract"] = relationship(back_populates="event")
    support: Mapped["Collaborator | None"] = relationship(back_populates="events")

    def has_support(self) -> bool:
        """Return True if a support collaborator is assigned to this event.

        Returns:
            bool: True if support_id is set, False if the event is unassigned.
        """
        return self.support_id is not None

    def duration_hours(self) -> float:
        """Return the duration of this event in hours.

        Calculated from the difference between end_date and start_date.

        Returns:
            float: Number of hours between start and end.
        """
        delta = self.end_date - self.start_date
        return delta.total_seconds() / 3600

    @property
    def is_past(self) -> bool:
        """Return True if this event has already ended.

        Compares end_date against the current UTC time. Used for
        filtering historical events in list views and reports.

        Returns:
            bool: True if end_date is before the current moment.
        """
        return self.end_date < datetime.now(timezone.utc)
