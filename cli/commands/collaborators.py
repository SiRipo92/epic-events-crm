"""
Collaborator management CLI commands.

Handles all collaborator-related menu interactions for Management.
No business logic lives here — handlers call service functions
and pass results to view functions.
"""

from __future__ import annotations

import questionary
from rich.console import Console
from sqlalchemy import Text, cast, select

from exceptions import (
    CollaboratorNotFoundError,
    DuplicateEmailError,
    PermissionDeniedError,
    ReassignmentRequiredError,
    ValidationError,
)
from models.client import Client
from models.collaborator import Collaborator
from models.contract import Contract
from models.event import Event
from services.collaborator_service import (
    create_collaborator,
    deactivate_collaborator,
    get_collaborator_by_id,
    get_collaborators,
    update_collaborator,
)
from views.messages import Errors, Info, Prompts, Success
from views.screens import render_collaborator_detail
from views.tables import (
    render_clients_table,
    render_collaborators_table,
    render_contracts_table,
    render_events_table,
)

console = Console()


# ── Main menu ─────────────────────────────────────────────────────────────────


def collaborators_menu(session, current_user: Collaborator) -> None:
    """Render the collaborators sub-menu for Management."""
    options = [
        "List Collaborators",
        "Create Collaborator",
        "Select Collaborator",
        Info.BACK,
    ]

    while True:
        choice = questionary.select(
            "Collaborators — select an option:",
            choices=options,
        ).ask()

        if choice is None or choice == Info.BACK:
            return

        if choice == "List Collaborators":
            _handle_list_collaborators(session, current_user)
        elif choice == "Create Collaborator":
            _handle_create_collaborator(session, current_user)
        elif choice == "Select Collaborator":
            _handle_select_collaborator(session, current_user)


# ── Selection and context menu ────────────────────────────────────────────────


def _select_collaborator_from_table(
    session, current_user: Collaborator
) -> Collaborator | None:
    """Show table and prompt for ID. Returns collaborator or None."""
    collaborators = get_collaborators(session=session, current_user=current_user)
    if not collaborators:
        console.print(Info.NO_COLLABORATORS)
        return None

    console.print(render_collaborators_table(collaborators))
    collaborator_id = questionary.text("Enter collaborator ID:").ask()

    if not collaborator_id:
        return None

    try:
        return get_collaborator_by_id(
            session=session,
            current_user=current_user,
            collaborator_id=int(collaborator_id),
        )
    except (CollaboratorNotFoundError, ValueError):
        console.print(Errors.NOT_FOUND)
        return None


def _handle_select_collaborator(session, current_user: Collaborator) -> None:
    """Select a collaborator and show context menu."""
    collaborator = _select_collaborator_from_table(session, current_user)
    if not collaborator:
        return
    _collaborator_context_menu(session, current_user, collaborator)


def _collaborator_context_menu(
    session, current_user: Collaborator, collaborator: Collaborator
) -> None:
    """Context menu for a selected collaborator."""
    assigned_count = 0
    clients_count = 0
    active_contracts_count = 0

    if collaborator.role and collaborator.role.name == "SUPPORT":
        result = session.execute(
            select(Event).where(
                Event.support_id == collaborator.id,
                Event.is_cancelled.is_(False),
            )
        )
        assigned_count = len(result.scalars().all())

    if collaborator.role and collaborator.role.name == "COMMERCIAL":
        clients_count = (
            session.query(Client)
            .filter(
                Client.commercial_id == collaborator.id,
            )
            .count()
        )
        active_contracts_count = (
            session.query(Contract)
            .filter(
                Contract.commercial_id == collaborator.id,
                cast(Contract.status, Text).notin_(["cancelled", "paid_in_full"]),
            )
            .count()
        )

    while True:
        render_collaborator_detail(
            collaborator,
            assigned_events_count=assigned_count,
            clients_count=clients_count,
            active_contracts_count=active_contracts_count,
        )

        if collaborator.is_active:
            actions = ["Update", "Deactivate", Info.BACK]
        else:
            actions = [Info.BACK]

        choice = questionary.select(
            f"{collaborator.full_name} — select an action:", choices=actions
        ).ask()

        if choice is None or choice == Info.BACK:
            return

        if choice == "Update":
            _handle_update_collaborator(session, current_user, collaborator)
        elif choice == "Deactivate":
            deactivated = _handle_deactivate_collaborator(
                session, current_user, collaborator
            )
            if deactivated:
                return  # exit context menu


# ── Handlers ──────────────────────────────────────────────────────────────────


def _handle_list_collaborators(session, current_user: Collaborator) -> None:
    """List all collaborators with optional role filter."""
    role_filter = questionary.select(
        "Filter by role:",
        choices=["All", "MANAGEMENT", "COMMERCIAL", "SUPPORT"],
    ).ask()

    role = None if role_filter == "All" else role_filter

    try:
        collaborators = get_collaborators(
            session=session,
            current_user=current_user,
            role=role,
        )
        if not collaborators:
            console.print(Info.NO_COLLABORATORS)
            return
        console.print(render_collaborators_table(collaborators))
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_create_collaborator(session, current_user: Collaborator) -> None:
    """Prompt for new collaborator details and create."""
    first_name = questionary.text("First name:").ask()
    last_name = questionary.text("Last name:").ask()
    email = questionary.text("Email address:").ask()
    role_name = questionary.select(
        "Role:",
        choices=["MANAGEMENT", "COMMERCIAL", "SUPPORT"],
    ).ask()
    password = questionary.password("Initial password:").ask()
    confirm = questionary.password("Confirm password:").ask()

    if password != confirm:
        console.print(Errors.PASSWORDS_DONT_MATCH)
        return

    role_map = {"MANAGEMENT": 1, "COMMERCIAL": 2, "SUPPORT": 3}
    role_id = role_map[role_name]

    try:
        collaborator = create_collaborator(
            session=session,
            current_user=current_user,
            first_name=first_name,
            last_name=last_name,
            email=email,
            role_id=role_id,
            password=password,
        )
        console.print(
            Success.COLLABORATOR_CREATED.format(
                name=collaborator.full_name,
                number=collaborator.employee_number,
            )
        )
    except DuplicateEmailError:
        console.print(Errors.DUPLICATE_EMAIL)
    except ValidationError as e:
        console.print(f"[red]✗ {e}[/red]")
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_update_collaborator(
    session, current_user: Collaborator, collaborator: Collaborator
) -> None:
    """Prompt for updated fields and save."""
    try:
        first_name = questionary.text(
            "First name:", default=collaborator.first_name
        ).ask()
        last_name = questionary.text("Last name:", default=collaborator.last_name).ask()
        email = questionary.text("Email:", default=collaborator.email).ask()
        phone = questionary.text("Phone:", default=collaborator.phone or "").ask()

        update_collaborator(
            session=session,
            current_user=current_user,
            collaborator=collaborator,
            first_name=first_name or None,
            last_name=last_name or None,
            email=email or None,
            phone=phone or None,
        )
        console.print(Success.COLLABORATOR_UPDATED.format(name=collaborator.full_name))
    except DuplicateEmailError:
        console.print(Errors.DUPLICATE_EMAIL)
    except ValidationError as e:
        console.print(f"[red]✗ {e}[/red]")
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_deactivate_collaborator(
    session, current_user: Collaborator, collaborator: Collaborator
) -> bool:
    """Confirm and deactivate collaborator. Returns True on success."""
    try:
        confirmed = questionary.confirm(Prompts.CONFIRM_DEACTIVATE).ask()

        if not confirmed:
            return False

        deactivate_collaborator(
            session=session,
            current_user=current_user,
            collaborator=collaborator,
        )
        console.print(Success.COLLABORATOR_DEACTIVATED)
        return True

    except ReassignmentRequiredError as e:
        console.print("\n[red]✗ Cannot deactivate — active dossiers exist.[/red]")
        console.print("[yellow]Reassign the following before deactivating:[/yellow]\n")
        if e.dossiers.get("clients"):
            console.print("[bold]Clients to reassign:[/bold]")
            console.print(render_clients_table(e.dossiers["clients"]))
        if e.dossiers.get("contracts"):
            console.print("[bold]Contracts to reassign:[/bold]")
            console.print(render_contracts_table(e.dossiers["contracts"]))
        if e.dossiers.get("events"):
            console.print("[bold]Events to reassign:[/bold]")
            console.print(render_events_table(e.dossiers["events"]))
        console.print(
            "\n[dim]→ Reassign via Clients, Contracts and Events "
            "menus, then retry.[/dim]"
        )
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)
