"""
Client management CLI commands.

Handles all client-related menu interactions scoped by role.
No business logic lives here — handlers call service functions
and pass results to view functions.
"""

from __future__ import annotations

import questionary
from rich.console import Console

from exceptions import (
    ClientNotFoundError,
    DuplicateEmailError,
    PermissionDeniedError,
    ValidationError,
)
from models.collaborator import Collaborator
from models.contract import Contract
from models.event import Event
from services.client_service import (
    create_client,
    get_client_by_id,
    get_clients_for_user,
    update_client,
)
from views.messages import Errors, Info, Success
from views.screens import render_client_detail
from views.tables import render_clients_table

console = Console()


# ── Main menu ─────────────────────────────────────────────────────────────────


def clients_menu(session, current_user: Collaborator) -> None:
    """Render the clients sub-menu scoped by role."""
    role = current_user.role.name

    if role == "COMMERCIAL":
        options = [
            "List Clients",
            "Create Client",
            "Select Client",
            Info.BACK,
        ]
    else:
        options = [
            "List Clients",
            "Select Client",
            Info.BACK,
        ]

    while True:
        choice = questionary.select(
            "Clients — select an option:",
            choices=options,
        ).ask()

        if choice is None or choice == Info.BACK:
            return

        if choice == "List Clients":
            _handle_list_clients(session, current_user)
        elif choice == "Create Client":
            _handle_create_client(session, current_user)
        elif choice == "Select Client":
            _handle_select_client(session, current_user)


# ── Selection and context menu ────────────────────────────────────────────────


def _select_client_from_table(session, current_user: Collaborator) -> object | None:
    """Show table and prompt for ID. Returns client or None."""
    clients = get_clients_for_user(session=session, current_user=current_user)
    if not clients:
        console.print(Info.NO_CLIENTS)
        return None

    console.print(render_clients_table(clients))
    client_id = questionary.text("Enter client ID:").ask()

    if not client_id:
        return None

    try:
        return get_client_by_id(
            session=session,
            current_user=current_user,
            client_id=int(client_id),
        )
    except (ClientNotFoundError, ValueError):
        console.print(Errors.NOT_FOUND)
        return None


def _handle_select_client(session, current_user: Collaborator) -> None:
    """Select a client and show context menu."""
    client = _select_client_from_table(session, current_user)
    if not client:
        return
    _client_context_menu(session, current_user, client)


def _client_context_menu(session, current_user, client) -> None:
    """Context menu for a selected client."""
    contracts = session.query(Contract).filter(Contract.client_id == client.id).all()

    support_ids = set()
    for contract in contracts:
        event = (
            session.query(Event)
            .filter(
                Event.contract_id == contract.id,
                Event.is_cancelled.is_(False),
            )
            .first()
        )
        if event and event.support_id:
            support_ids.add(event.support_id)

    role = current_user.role.name

    while True:
        render_client_detail(
            client,
            contracts_summary=contracts,
            support_ids=support_ids,
        )

        if role == "COMMERCIAL" and client.commercial_id == current_user.id:
            actions = ["Update", Info.BACK]
        else:
            actions = [Info.BACK]

        choice = questionary.select(
            f"{client.full_name} — select an action:",
            choices=actions,
        ).ask()

        if choice is None or choice == Info.BACK:
            return

        if choice == "Update":
            _handle_update_client(session, current_user, client)


# ── Handlers ──────────────────────────────────────────────────────────────────


def _handle_list_clients(session, current_user: Collaborator) -> None:
    """List clients scoped by role with optional filter."""
    filter_by = questionary.select(
        "Filter by:",
        choices=["None", "Client name", "Company name"],
    ).ask()

    name_filter = None
    company_filter = None

    if filter_by == "Client name":
        name_filter = questionary.text("Enter client name:").ask()
    elif filter_by == "Company name":
        company_filter = questionary.text("Enter company name:").ask()

    try:
        clients = get_clients_for_user(session=session, current_user=current_user)

        if name_filter:
            name_filter = name_filter.lower()
            clients = [c for c in clients if name_filter in c.full_name.lower()]
        if company_filter:
            company_filter = company_filter.lower()
            clients = [
                c
                for c in clients
                if c.company_name and company_filter in c.company_name.lower()
            ]

        if not clients:
            console.print(Info.NO_CLIENTS)
            return
        console.print(render_clients_table(clients))
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_create_client(session, current_user: Collaborator) -> None:
    """Prompt for new client details and create."""
    first_name = questionary.text("First name:").ask()
    last_name = questionary.text("Last name:").ask()
    email = questionary.text("Email address:").ask()
    phone = questionary.text("Phone (optional):").ask()
    company_name = questionary.text("Company name (optional):").ask()

    try:
        client = create_client(
            session=session,
            current_user=current_user,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone or None,
            company_name=company_name or None,
        )
        console.print(Success.CLIENT_CREATED.format(name=client.full_name))
    except DuplicateEmailError:
        console.print(Errors.DUPLICATE_EMAIL)
    except ValidationError as e:
        console.print(f"[red]✗ {e}[/red]")
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)


def _handle_update_client(session, current_user: Collaborator, client) -> None:
    """Prompt for updated client fields and save."""
    try:
        first_name = questionary.text("First name:", default=client.first_name).ask()
        last_name = questionary.text("Last name:", default=client.last_name).ask()
        email = questionary.text("Email:", default=client.email).ask()
        phone = questionary.text("Phone:", default=client.phone or "").ask()
        company_name = questionary.text(
            "Company name:", default=client.company_name or ""
        ).ask()

        update_client(
            session=session,
            current_user=current_user,
            client=client,
            first_name=first_name or None,
            last_name=last_name or None,
            email=email or None,
            phone=phone or None,
            company_name=company_name or None,
        )
        console.print(Success.CLIENT_UPDATED.format(name=client.full_name))
    except DuplicateEmailError:
        console.print(Errors.DUPLICATE_EMAIL)
    except ValidationError as e:
        console.print(f"[red]✗ {e}[/red]")
    except PermissionDeniedError:
        console.print(Errors.PERMISSION_DENIED)
