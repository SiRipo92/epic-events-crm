"""
Event management CLI commands.

Handles all event-related menu interactions scoped by role.
No business logic lives here — handlers call service functions
and pass results to view functions.
"""

from __future__ import annotations

import questionary
from rich.console import Console
from sqlalchemy import select

from models.collaborator import Collaborator
from models.contract import Contract, ContractStatus
from models.event import Event
from services.event_service import (
    assign_support,
    create_event,
    filter_events,
    get_all_events,
    get_event_by_id,
    get_events_for_user,
    update_event,
)
from utils.exceptions import (
    ContractNotEligibleError,
    EventNotFoundError,
    InvalidAssignmentError,
    PermissionDeniedError,
    SchedulingConflictWarning,
    ValidationError,
)
from views.messages import Errors, Info, Prompts, Success, Warnings
from views.screens import render_event_detail
from views.tables import render_events_table

console = Console()


# ── Main menu ─────────────────────────────────────────────────────────────────


def events_menu(session, current_user: Collaborator) -> None:
    """Render the events sub-menu scoped by role."""
    role = current_user.role.name

    if role == "MANAGEMENT":
        options = [
            "List Events",
            "Events Needing Support",
            "Select Event",
            Info.BACK,
        ]
    elif role == "COMMERCIAL":
        options = [
            "List Events",
            "Create Event",
            "Select Event",
            Info.BACK,
        ]
    else:  # SUPPORT
        options = [
            "List Events",
            "My Events",
            "Select Event",
            Info.BACK,
        ]

    while True:
        choice = questionary.select(
            "Events — select an option:",
            choices=options,
        ).ask()

        if choice is None or choice == Info.BACK:
            return

        if choice == "List Events":
            _handle_list_events(session, current_user)
        elif choice == "My Events":
            _handle_my_events(session, current_user)
        elif choice == "Events Needing Support":
            _handle_events_needing_support(session, current_user)
        elif choice == "Create Event":
            _handle_create_event(session, current_user)
        elif choice == "Select Event":
            _handle_select_event(session, current_user)


# ── Selection and context menu ────────────────────────────────────────────────


def _select_event_from_table(
    session,
    current_user: Collaborator,
    events: list[Event] | None = None,
) -> Event | None:
    """Show table and prompt for ID. Returns event or None."""
    if events is None:
        events = get_all_events(session=session, current_user=current_user)
    if not events:
        console.print(Info.NO_EVENTS)
        return None

    console.print(render_events_table(events))
    event_id = questionary.text("Enter event ID:").ask()

    if not event_id:
        return None

    try:
        return get_event_by_id(
            session=session,
            current_user=current_user,
            event_id=int(event_id),
        )
    except (EventNotFoundError, ValueError):
        console.print(Errors.NOT_FOUND)
        return None


def _handle_select_event(session, current_user: Collaborator) -> None:
    """Select an event and show context menu."""
    event = _select_event_from_table(session, current_user)
    if not event:
        return
    _event_context_menu(session, current_user, event)


def _event_context_menu(session, current_user: Collaborator, event: Event) -> None:
    """Context menu for a selected event — actions scoped by role."""
    role = current_user.role.name

    while True:
        render_event_detail(event)

        if role == "MANAGEMENT":
            if not event.has_support:
                actions = ["Assign Support", Info.BACK]
            else:
                actions = ["Reassign Support", Info.BACK]
        elif role == "SUPPORT" and event.support_id == current_user.id:
            actions = ["Update Event", Info.BACK]
        else:
            actions = [Info.BACK]

        choice = questionary.select(
            f"Event — {event.title} — select an action:",
            choices=actions,
        ).ask()

        if choice is None or choice == Info.BACK:
            return

        if choice in ("Assign Support", "Reassign Support"):
            _handle_assign_support(session, current_user, event)
        elif choice == "Update Event":
            _handle_update_event(session, current_user, event)


# ── Handlers ──────────────────────────────────────────────────────────────────


def _handle_list_events(session, current_user: Collaborator) -> None:
    """List events scoped by role with optional filter."""
    role = current_user.role.name

    filter_choices = ["None", "Upcoming", "Past"]
    if role == "MANAGEMENT":
        filter_choices.append("Unassigned Support")
    if role == "SUPPORT":
        filter_choices.append("My Events")

    filter_by = questionary.select("Filter by:", choices=filter_choices).ask()

    try:
        events = get_all_events(session=session, current_user=current_user)

        if filter_by == "Upcoming":
            events = filter_events(events, upcoming=True)
        elif filter_by == "Past":
            events = filter_events(events, past=True)
        elif filter_by == "Unassigned Support":
            events = filter_events(events, support_unassigned=True)
        elif filter_by == "My Events":
            events = [e for e in events if e.support_id == current_user.id]

        if not events:
            console.print(Info.NO_EVENTS)
            return

        console.print(render_events_table(events))

        # Highlight past events with outstanding balance for Management
        if role == "MANAGEMENT":
            payment_due = [
                e
                for e in events
                if e.is_past
                and e.contract is not None
                and e.contract.remaining_amount > 0
            ]
            if payment_due:
                console.print(
                    f"\n[yellow]⚠ {len(payment_due)} past event(s) "
                    f"with outstanding balance — check Contracts.[/yellow]"
                )

    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_events_needing_support(session, current_user: Collaborator) -> None:
    """Show pre-filtered list of unassigned events for Management."""
    try:
        events = get_events_for_user(session=session, current_user=current_user)
        unassigned = filter_events(events, support_unassigned=True)

        if not unassigned:
            console.print("[green]✓ All events have support assigned.[/green]")
            return

        console.print(
            f"\n[yellow]⚠ {len(unassigned)} event(s) need "
            f"support assignment:[/yellow]\n"
        )
        console.print(render_events_table(unassigned))

        assign_now = questionary.confirm("Select an event to assign support now?").ask()

        if not assign_now:
            return

        event = _select_event_from_table(session, current_user, events=unassigned)
        if event:
            _handle_assign_support(session, current_user, event)

    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_create_event(session, current_user: Collaborator) -> None:
    """Prompt Commercial to create event from DEPOSIT_RECEIVED contract."""
    from datetime import datetime

    # Show only DEPOSIT_RECEIVED contracts for this commercial
    contracts = (
        session.query(Contract)
        .filter(
            Contract.commercial_id == current_user.id,
            Contract.status == ContractStatus.DEPOSIT_RECEIVED,
        )
        .all()
    )

    if not contracts:
        console.print(
            "[red]✗ No eligible contracts found. A contract must "
            "be in DEPOSIT_RECEIVED status to create an event.[/red]"
        )
        return

    contract_choices = [
        f"{c.id} — {c.client.full_name if c.client else '—'} "
        f"({c.remaining_amount:.2f} € remaining)"
        for c in contracts
    ]
    contract_choices.append(Info.BACK)

    contract_choice = questionary.select(
        "Select contract:", choices=contract_choices
    ).ask()

    if not contract_choice or contract_choice == Info.BACK:
        return

    contract_id = int(contract_choice.split(" — ")[0])
    contract = next(c for c in contracts if c.id == contract_id)

    title = questionary.text("Event title:").ask()
    if not title:
        return

    start_str = questionary.text("Start date (DD/MM/YYYY HH:MM):").ask()
    end_str = questionary.text("End date (DD/MM/YYYY HH:MM):").ask()

    try:
        start_date = datetime.strptime(start_str, "%d/%m/%Y %H:%M")
        end_date = datetime.strptime(end_str, "%d/%m/%Y %H:%M")
    except ValueError:
        console.print("[red]✗ Invalid date format. Use DD/MM/YYYY HH:MM.[/red]")
        return

    location_street = questionary.text("Street address:").ask()
    location_city = questionary.text("City:").ask()
    location_zip = questionary.text("Zip code:").ask()
    location_country = questionary.text("Country:", default="France").ask()
    attendees_str = questionary.text("Expected attendees:", default="0").ask()
    notes = questionary.text("Notes (optional):").ask()

    try:
        attendees = int(attendees_str or 0)
    except ValueError:
        attendees = 0

    try:
        event = create_event(
            session=session,
            current_user=current_user,
            contract=contract,
            title=title,
            start_date=start_date,
            end_date=end_date,
            location_street=location_street,
            location_city=location_city,
            location_zip=location_zip,
            location_country=location_country or "France",
            attendees=attendees,
            notes=notes or None,
        )
        console.print(Success.EVENT_CREATED.format(title=event.title))
    except (ContractNotEligibleError, PermissionDeniedError, ValidationError) as e:
        console.print(f"[red]✗ {e}[/red]")


def _handle_my_events(session, current_user: Collaborator) -> None:
    """Show only events assigned to the current support member."""
    events = get_all_events(session=session, current_user=current_user)
    my_events = [e for e in events if e.support_id == current_user.id]

    if not my_events:
        console.print("[dim]No events are currently assigned to you.[/dim]")
        return

    console.print(render_events_table(my_events))


def _handle_assign_support(session, current_user: Collaborator, event: Event) -> None:
    """Show support availability and assign to event."""
    from models.role import Role

    # Get all Support collaborators
    support_members = (
        session.query(Collaborator)
        .join(Role)
        .filter(
            Role.name == "SUPPORT",
            Collaborator.is_active.is_(True),
        )
        .all()
    )

    if not support_members:
        console.print("[red]✗ No active Support members found.[/red]")
        return

    # Build availability info
    event_date = event.start_date.date()
    console.print(
        f"\n[cyan]Support availability for "
        f"{event_date.strftime('%d/%m/%Y')}:[/cyan]\n"
    )

    support_choices = []
    for s in support_members:
        existing = (
            session.execute(
                select(Event).where(
                    Event.support_id == s.id,
                    Event.is_cancelled.is_(False),
                )
            )
            .scalars()
            .all()
        )

        same_day = [e for e in existing if e.start_date.date() == event_date]
        conflict_str = (
            f"[yellow]⚠ {len(same_day)} event(s) on this date[/yellow]"
            if same_day
            else "[green]✓ Available[/green]"
        )
        console.print(
            f"  {s.id} — {s.full_name} — "
            f"{len(existing)} total event(s) — {conflict_str}"
        )
        support_choices.append(
            f"{s.id} — {s.full_name}" + (" ⚠ CONFLICT" if same_day else "")
        )

    support_choices.append(Info.BACK)
    console.print()

    support_choice = questionary.select(
        "Select support member:", choices=support_choices
    ).ask()

    if not support_choice or support_choice == Info.BACK:
        return

    support_id = int(support_choice.split(" — ")[0])
    support = next(s for s in support_members if s.id == support_id)

    try:
        assign_support(
            session=session,
            current_user=current_user,
            event=event,
            support=support,
        )
        console.print(Success.SUPPORT_ASSIGNED)

    except SchedulingConflictWarning:
        console.print(
            Warnings.SCHEDULING_CONFLICT.format(
                name=support.full_name,
                date=event_date.strftime("%d/%m/%Y"),
            )
        )
        force = questionary.confirm(Prompts.FORCE_ASSIGN).ask()
        if not force:
            return
        # Force assign by directly setting support_id
        event.support_id = support.id
        session.commit()
        console.print(Success.SUPPORT_ASSIGNED)

    except (InvalidAssignmentError, PermissionDeniedError) as e:
        console.print(f"[red]✗ {e}[/red]")


def _handle_update_event(session, current_user: Collaborator, event: Event) -> None:
    """Prompt Support to update their assigned event."""
    try:
        title = questionary.text("Title:", default=event.title).ask()
        location_street = questionary.text(
            "Street:", default=event.location_street or ""
        ).ask()
        location_city = questionary.text(
            "City:", default=event.location_city or ""
        ).ask()
        location_zip = questionary.text("Zip:", default=event.location_zip or "").ask()
        location_country = questionary.text(
            "Country:", default=event.location_country or "France"
        ).ask()
        attendees_str = questionary.text(
            "Attendees:", default=str(event.attendees)
        ).ask()
        notes = questionary.text("Notes:", default=event.notes or "").ask()

        try:
            attendees = int(attendees_str or 0)
        except ValueError:
            attendees = event.attendees

        update_event(
            session=session,
            current_user=current_user,
            event=event,
            title=title or None,
            location_street=location_street or None,
            location_city=location_city or None,
            location_zip=location_zip or None,
            location_country=location_country or None,
            attendees=attendees,
            notes=notes or None,
        )
        console.print(Success.EVENT_UPDATED.format(title=event.title))
    except (PermissionDeniedError, ValidationError) as e:
        console.print(f"[red]✗ {e}[/red]")
