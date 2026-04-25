"""
Event service.

Handles all event management operations — creation, support assignment,
update, and retrieval.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from models.event import Event
from permissions.decorators import require_role
from utils.exceptions import (
    ContractNotEligibleError,
    EventNotFoundError,
    InvalidAssignmentError,
    PermissionDeniedError,
    SchedulingConflictWarning,
)
from utils.validation import validate_event_dates, validate_location

# ── Event  Helper ─────────────────────────────────────────────────────────────────


def _event_not_found(event_id: int) -> EventNotFoundError:
    """Return an EventNotFoundError for the given ID."""
    return EventNotFoundError(f"No event found with ID {event_id}.")


# ── Public Interface ─────────────────────────────────────────────────────────────────


@require_role("COMMERCIAL")
def create_event(
    session: Session,
    current_user: Collaborator,
    contract: Contract,
    title: str,
    start_date: datetime,
    end_date: datetime,
    location_street: str | None = None,
    location_zip: str | None = None,
    location_city: str | None = None,
    location_country: str | None = None,
    attendees: int = 0,
    notes: str | None = None,
) -> Event:
    """Create a new event linked to a DEPOSIT_RECEIVED contract.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Commercial collaborator.
        contract: The Contract instance to link the event to.
        title: Event title.
        start_date: Event start date and time.
        end_date: Event end date and time.
        location_street: Required street address.
        location_zip: Required zip code.
        location_city: Required city.
        location_country: Optional country, defaults to France.
        attendees: Expected number of attendees.
        notes: Optional notes.

    Returns:
        Event: The newly created event instance.

    Raises:
        PermissionDeniedError: If current_user is not Commercial or
                               does not own the contract.
        ContractNotEligibleError: If contract status is not
                                  DEPOSIT_RECEIVED.
        ValidationError: If location fields are missing or dates invalid.
    """
    # Step 1 — Ownership check
    if contract.commercial_id != current_user.id:
        raise PermissionDeniedError(
            "You can only create events from your own contracts."
        )

    # Step 2 — Validate contract status
    if contract.status != ContractStatus.DEPOSIT_RECEIVED:
        raise ContractNotEligibleError(
            f"Cannot create event: contract status is "
            f"{contract.status.value}, expected DEPOSIT_RECEIVED."
        )

    # Step 3 — Validate location
    validate_location(location_street, location_city, location_zip)

    # Step 4 — Validate dates
    validate_event_dates(start_date, end_date)

    # Step 5 — Build event
    event = Event()
    event.contract_id = contract.id
    event.title = title
    event.start_date = start_date
    event.end_date = end_date
    event.location_street = location_street
    event.location_zip = location_zip
    event.location_city = location_city
    event.location_country = location_country
    event.attendees = attendees
    event.notes = notes
    event.support_id = None

    session.add(event)
    session.commit()

    return event


@require_role("SUPPORT")
def update_event(
    session: Session,
    current_user: Collaborator,
    event: Event,
    title: str | None = None,
    location_street: str | None = None,
    location_zip: str | None = None,
    location_city: str | None = None,
    location_country: str | None = None,
    attendees: int | None = None,
    notes: str | None = None,
) -> Event:
    """Update allowed fields on an assigned event.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Support collaborator.
        event: The Event instance to update.
        title: New title, or None to leave unchanged.
        location_street: New street, or None to leave unchanged.
        location_zip: New zip code, or None to leave unchanged.
        location_city: New city, or None to leave unchanged.
        location_country: New country, or None to leave unchanged.
        attendees: New attendee count, or None to leave unchanged.
        notes: New notes, or None to leave unchanged.

    Returns:
        Event: The updated event instance.

    Raises:
        PermissionDeniedError: If current_user is not Support or
                               is not assigned to this event.
    """
    # Step 1 — Ownership check
    if event.support_id != current_user.id:
        raise PermissionDeniedError("You can only update events assigned to you.")

    # Step 2 — Apply updates
    if title is not None:
        event.title = title

    if location_street is not None:
        event.location_street = location_street

    if location_zip is not None:
        event.location_zip = location_zip

    if location_city is not None:
        event.location_city = location_city

    if location_country is not None:
        event.location_country = location_country

    if attendees is not None:
        event.attendees = attendees

    if notes is not None:
        event.notes = notes

    session.commit()
    return event


@require_role("MANAGEMENT")
def assign_support(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    event: Event,
    support: Collaborator,
) -> Event:
    """Assign a support collaborator to an event.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Management collaborator.
        event: The Event instance to assign support to.
        support: The Collaborator to assign as support.

    Returns:
        Event: The updated event instance.

    Raises:
        PermissionDeniedError: If current_user is not Management.
        InvalidAssignmentError: If support is not a Support collaborator.
        SchedulingConflictWarning: If support has another event on the
                                   same date.
    """
    # Step 1 — Validate support role
    if support.role.name != "SUPPORT":
        raise InvalidAssignmentError(
            f"{support.full_name} is not a Support collaborator."
        )

    # Step 2 — Check for scheduling conflict
    event_date = event.start_date.date()
    existing_events = list(
        session.scalars(
            select(Event)
            .where(Event.support_id == support.id)
            .where(Event.is_cancelled.is_(False))
        ).all()
    )
    conflict = any(e.start_date.date() == event_date for e in existing_events)
    if conflict:
        raise SchedulingConflictWarning(
            f"{support.full_name} already has an event on "
            f"{event_date}. Management can still force assign."
        )

    # Step 3 — Assign support
    event.support_id = support.id
    session.commit()
    return event


@require_role("MANAGEMENT", "COMMERCIAL", "SUPPORT")
def get_events_for_user(
    session: Session,
    current_user: Collaborator,
) -> list[Event]:
    """Return events scoped to the current user's role.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated collaborator.

    Returns:
        list[Event]: Events visible to the current user.

    Raises:
        PermissionDeniedError: If current_user has no valid role.
    """
    if current_user.role.name == "MANAGEMENT":
        return list(session.scalars(select(Event)).all())

    if current_user.role.name == "COMMERCIAL":
        return list(
            session.scalars(
                select(Event)
                .join(Contract, Contract.id == Event.contract_id)
                .where(Contract.commercial_id == current_user.id)
            ).all()
        )

    # SUPPORT
    return list(
        session.scalars(select(Event).where(Event.support_id == current_user.id)).all()
    )


def filter_events(
    events: list[Event],
    support_unassigned: bool | None = None,
    upcoming: bool | None = None,
    past: bool | None = None,
    payment_due: bool | None = None,
) -> list[Event]:
    """Filter a list of events by optional criteria.

    Filters are applied on top of a pre-fetched list — never issues
    additional DB queries.
    """
    results = events

    if support_unassigned:
        results = [e for e in results if e.support_id is None]

    if upcoming:
        now = datetime.now(timezone.utc)
        results = [e for e in results if e.start_date >= now]

    if upcoming is not None and not upcoming:
        results = [e for e in results if e.is_past]

    if past:
        results = [e for e in results if e.is_past]

    return results


@require_role("MANAGEMENT", "COMMERCIAL", "SUPPORT")
def get_event_by_id(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
    event_id: int,
) -> Event:
    """Return a single event by ID. All roles have read access.

    Raises:
        EventNotFoundError: If event does not exist.
    """
    event: Event | None = session.get(Event, event_id)
    if not event:
        raise _event_not_found(event_id)
    return event


@require_role("MANAGEMENT", "COMMERCIAL", "SUPPORT")
def get_all_events(
    session: Session,
    current_user: Collaborator,  # noqa: ARG001 — consumed by @require_role
) -> list[Event]:
    """Return all events. All roles have read access to all events.

    Args:
        session: SQLAlchemy database session.
        current_user: Any authenticated collaborator.

    Returns:
        list[Event]: All events in the system.
    """
    return list(session.scalars(select(Event)).all())
