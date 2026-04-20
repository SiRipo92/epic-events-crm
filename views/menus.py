"""
Menu renderers and navigation for the Epic Events CRM CLI.

All menu logic lives here. Each function renders a questionary
menu, collects user input, and dispatches to the appropriate
handler. No business logic lives here — menus call service
functions and pass results to view functions.
"""

from __future__ import annotations

import questionary
from rich.console import Console
from rich.panel import Panel

from cli.commands.clients import clients_menu

# from cli.commands.contracts import contracts_menu
# from cli.commands.events import events_menu
from cli.commands.collaborators import collaborators_menu
from db.session import get_session
from exceptions import AuthenticationError, ValidationError
from services.auth_service import (
    change_password,
    complete_first_login,
    get_session_user,
    login,
    logout,
)
from views.messages import Errors, Info, Success
from views.screens import show_password_change_screen

console = Console()


# ── App entry point ───────────────────────────────────────────────────────────


def run_app() -> None:
    """Main entry point for the Epic Events CRM.

    Detects existing session or prompts for login.
    Routes to password change screen if required.
    Launches role-scoped main menu.
    """
    with get_session() as session:
        # Step 1 — check for existing session
        try:
            current_user = get_session_user(session)
        except AuthenticationError:
            current_user = None

        # Step 2 — login if no valid session
        if not current_user:
            current_user = _show_login_screen(session)
            if not current_user:
                return

        # Step 3 — first login password gate
        if current_user.must_change_password:
            _handle_password_change(session, current_user)

        # Step 4 — launch role-scoped main menu
        _show_main_menu(session, current_user)


# ── Login screen ──────────────────────────────────────────────────────────────


def _show_login_screen(session) -> object | None:
    """Prompt for email and password until login succeeds.

    Returns:
        Collaborator | None: The authenticated collaborator, or None
                             if the user cancels.
    """
    console.print(
        Panel(
            "[cyan]Welcome to Epic Events CRM[/cyan]",
            border_style="cyan",
        )
    )

    while True:
        email = questionary.text("Email address:").ask()
        if email is None:
            return None

        password = questionary.password("Password:").ask()
        if password is None:
            return None

        try:
            collaborator = login(session, email, password)
            console.print(Success.LOGIN_OK.format(name=collaborator.first_name))
            return collaborator
        except AuthenticationError as e:
            console.print(f"[red]✗ {e}[/red]")


# ── Password change ───────────────────────────────────────────────────────────


def _handle_password_change(session, current_user) -> None:
    """Route to password change screen and clear the flag on success.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Collaborator.
    """
    console.print(Errors.MUST_CHANGE_PASSWORD)

    while True:
        current_password, new_password = show_password_change_screen()
        try:
            change_password(session, current_user, current_password, new_password)
            complete_first_login(session, current_user)
            console.print(Success.PASSWORD_CHANGED)
            return
        except (AuthenticationError, ValidationError) as e:
            console.print(f"[red]✗ {e}[/red]")


# ── Main menu ─────────────────────────────────────────────────────────────────


def _show_main_menu(session, current_user) -> None:
    """Render the role-scoped main menu loop.

    Args:
        session: SQLAlchemy database session.
        current_user: The authenticated Collaborator.
    """
    role = current_user.role.name

    if role == "MANAGEMENT":
        options = [
            "Clients",
            "Contracts",
            "Events",
            "Collaborators",
            Info.LOGOUT,
        ]
    elif role == "COMMERCIAL":
        options = [
            "My Clients",
            "My Contracts",
            "Events",
            Info.LOGOUT,
        ]
    else:  # SUPPORT
        options = [
            "My Events",
            Info.LOGOUT,
        ]

    while True:
        console.print(
            Panel(
                f"[cyan]Logged in as {current_user.full_name} " f"— {role}[/cyan]",
                border_style="cyan",
            )
        )

        choice = questionary.select(
            "Main Menu — select an option:",
            choices=options,
        ).ask()

        if choice is None or choice == Info.LOGOUT:
            logout()
            console.print(Success.LOGGED_OUT)
            return

        if choice in ("Clients", "My Clients"):
            clients_menu(session, current_user)
            pass
        elif choice in ("Contracts", "My Contracts"):
            # contracts_menu(session, current_user)
            pass
        elif choice in ("Events", "My Events"):
            # events_menu(session, current_user)
            pass
        elif choice == "Collaborators":
            collaborators_menu(session, current_user)
            pass
