"""
Rich screen renderers for the Epic Events CRM CLI.

Detail panels, password change screen, and other full-screen
views. No business logic lives here — screens receive data
and render it, or collect input and return it.
"""

from __future__ import annotations

import questionary
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from exceptions import ValidationError
from models.client import Client
from models.collaborator import Collaborator
from models.contract import Contract
from models.event import Event
from utils.validation import validate_password
from views.messages import Errors, Prompts

console = Console()


# ── Password screens ──────────────────────────────────────────────────────────


def show_password_change_screen() -> tuple[str, str]:
    """Prompt the user for a password change.

    Prompts for current password, new password, and confirmation.
    Loops until new password and confirmation match.

    Returns:
        tuple[str, str]: (current_password, new_password)
    """
    console.print(
        Panel(
            "[yellow]You must change your password before continuing.[/yellow]",
            title="Password Change Required",
            border_style="yellow",
        )
    )

    current_password = questionary.password(Prompts.CURRENT_PASSWORD).ask()

    while True:
        new_password = questionary.password(Prompts.NEW_PASSWORD).ask()
        confirm_password = questionary.password(Prompts.CONFIRM_PASSWORD).ask()

        if new_password != confirm_password:
            console.print(Errors.PASSWORDS_DONT_MATCH)
            continue

        try:
            validate_password(new_password)
        except ValidationError:
            console.print(Errors.WEAK_PASSWORD)
            continue

        return current_password, new_password


# ── Collaborator detail ───────────────────────────────────────────────────────


def render_collaborator_detail(collaborator: Collaborator) -> None:
    """Render a full detail panel for a single collaborator.

    Args:
        collaborator: The Collaborator instance to display.
    """
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Employee No.", collaborator.employee_number)
    table.add_row("Name", collaborator.full_name)
    table.add_row("Email", collaborator.email)
    table.add_row("Phone", collaborator.phone or "—")
    table.add_row(
        "Role",
        collaborator.role.name if collaborator.role else "—",
    )
    table.add_row(
        "Active",
        "[green]Yes[/green]" if collaborator.is_active else "[red]No[/red]",
    )
    table.add_row(
        "Must change password",
        "[yellow]Yes[/yellow]" if collaborator.must_change_password else "No",
    )

    console.print(
        Panel(
            table,
            title=f"Collaborator — {collaborator.full_name}",
            border_style="cyan",
        )
    )


# ── Client detail ─────────────────────────────────────────────────────────────


def render_client_detail(client: Client) -> None:
    """Render a full detail panel for a single client.

    Args:
        client: The Client instance to display.
    """
    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Name", client.full_name)
    table.add_row("Email", client.email)
    table.add_row("Phone", client.phone or "—")
    table.add_row("Company", client.company_name or "—")
    table.add_row("Commercial ID", str(client.commercial_id))
    table.add_row(
        "Created",
        client.created_at.strftime("%d/%m/%Y") if client.created_at else "—",
    )
    table.add_row(
        "Updated",
        client.updated_at.strftime("%d/%m/%Y") if client.updated_at else "—",
    )

    console.print(
        Panel(
            table,
            title=f"Client — {client.full_name}",
            border_style="cyan",
        )
    )


# ── Contract detail ───────────────────────────────────────────────────────────


def render_contract_detail(contract: Contract) -> None:
    """Render a full detail panel for a single contract.

    Args:
        contract: The Contract instance to display.
    """
    from views.tables import CONTRACT_STATUS_STYLE

    status_style = CONTRACT_STATUS_STYLE.get(contract.status, "")
    client_name = contract.client.full_name if contract.client else "—"

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Contract ID", str(contract.id))
    table.add_row("Client", client_name)
    table.add_row("Commercial ID", str(contract.commercial_id))
    table.add_row("Total Amount", f"{contract.total_amount:.2f} €")
    table.add_row("Remaining", f"{contract.remaining_amount:.2f} €")
    table.add_row(
        "Deposit Received",
        "[green]Yes[/green]" if contract.deposit_received else "[dim]No[/dim]",
    )
    table.add_row(
        "Status",
        f"[{status_style}]{contract.status.value.upper()}[/{status_style}]",
    )
    table.add_row(
        "Created",
        contract.created_at.strftime("%d/%m/%Y") if contract.created_at else "—",
    )
    table.add_row(
        "Updated",
        contract.updated_at.strftime("%d/%m/%Y") if contract.updated_at else "—",
    )

    console.print(
        Panel(
            table,
            title=f"Contract #{contract.id}",
            border_style="cyan",
        )
    )


# ── Event detail ──────────────────────────────────────────────────────────────


def render_event_detail(event: Event) -> None:
    """Render a full detail panel for a single event.

    Args:
        event: The Event instance to display.
    """
    status = (
        "[red]Cancelled[/red]"
        if event.is_cancelled
        else "[yellow]Past[/yellow]" if event.is_past else "[green]Upcoming[/green]"
    )

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    table.add_column("Field", style="dim")
    table.add_column("Value")

    table.add_row("Title", event.title)
    table.add_row("Contract ID", str(event.contract_id))
    table.add_row("Start", event.start_date.strftime("%d/%m/%Y %H:%M"))
    table.add_row("End", event.end_date.strftime("%d/%m/%Y %H:%M"))
    table.add_row("Location", event.location or "—")
    table.add_row("Attendees", str(event.attendees))
    table.add_row("Notes", event.notes or "—")
    table.add_row(
        "Support ID",
        str(event.support_id) if event.support_id else "[dim]Unassigned[/dim]",
    )
    table.add_row("Status", status)
    table.add_row(
        "Created",
        event.created_at.strftime("%d/%m/%Y") if event.created_at else "—",
    )
    table.add_row(
        "Updated",
        event.updated_at.strftime("%d/%m/%Y") if event.updated_at else "—",
    )

    console.print(
        Panel(
            table,
            title=f"Event — {event.title}",
            border_style="cyan",
        )
    )
