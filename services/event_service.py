"""
Event service.

Handles all event management operations — creation, support assignment,
update, and retrieval.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from exceptions import ContractNotEligibleError, PermissionDeniedError
from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from models.event import Event
from permissions.decorators import require_role
from utils.validation import validate_event_dates, validate_location

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
    # Step 1 — ownership check
    if event.support_id != current_user.id:
        raise PermissionDeniedError("You can only update events assigned to you.")

    # Step 2 — apply updates
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
