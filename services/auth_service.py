"""
Authentication service.

Handles login, logout, session token management, and current user
resolution. All authentication logic lives here — never in the CLI
or view layer.

Session tokens are JWT tokens stored at ~/.epic_events/session
with chmod 600. They expire after 8 hours.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import sentry_sdk
from sqlalchemy.orm import Session

from config import settings
from exceptions import AuthenticationError, ValidationError
from models.collaborator import Collaborator
from utils.validation import validate_password

# ── Session file helpers ───────────────────────────────────────────────────────


def _get_session_path() -> Path:
    """Return the path to the session token file."""
    return settings.session_file


def _write_session_file(token: str) -> None:
    """
    Write a JWT token to the session file with restricted permissions.

    Creates the parent directory if it does not exist.
    Sets file permissions to 600 (owner read/write only).
    """
    session_path = _get_session_path()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(token)
    os.chmod(session_path, 0o600)


def _read_session_file() -> str | None:
    """
    Read the JWT token from session file.

    Return None if the session file does not exist.
    """
    session_path = _get_session_path()
    if not session_path.exists():
        return None
    return session_path.read_text().strip()


def _delete_session_file() -> None:
    """Delete the session file if it exists."""
    session_path = _get_session_path()
    if session_path.exists():
        session_path.unlink()


# ── Token helpers ─────────────────────────────────────────────────────────────


def _generate_token(collaborator) -> str:
    """
    Generate a signed JWT token for the given collaborator.

    Args:
        collaborator: The authenticated Collaborator instance.

    Returns:
        str: Encoded JWT token string.
    """
    payload = {
        "user_id": collaborator.id,
        "role": collaborator.role.name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expiry_hours),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def _decode_token(token: str) -> dict:
    """
    Decode and verify JWT token.

    Args:
        token: The raw JWT string to decode.

    Returns:
        dict: The decoded payload containing user_id, role, exp.

    Raises:
        AuthenticationError: If the token is expired or invalid.
    """
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid session. Please log in again.")


# ── Public interface ──────────────────────────────────────────────────────────


def login(session: Session, email: str, password: str) -> Collaborator:
    """Authenticate a collaborator and create a session token.

    Checks credentials and active status, then writes a JWT to the
    session file. Returns the collaborator regardless of
    must_change_password — the caller is responsible for checking
    that flag and routing to the password change screen if needed.
    Failed login attempts are captured in Sentry for audit purposes.

    Args:
        session: SQLAlchemy database session.
        email: The collaborator's email address.
        password: The plaintext password to verify.

    Returns:
        Collaborator: The authenticated collaborator instance.

    Raises:
        AuthenticationError: If credentials are invalid or account
                             is deactivated.
    """
    # Step 1 — look up by email
    collaborator: Collaborator | None = (
        session.query(Collaborator).filter_by(email=email).first()
    )

    # Step 2 — verify password (same error as unknown email — no enumeration)
    if not collaborator or not collaborator.verify_password(password):
        sentry_sdk.capture_message(
            f"Failed login attempt for email: {email}",
            level="warning",
        )
        raise AuthenticationError("Invalid credentials. Please try again.")

    # Step 3 — check active status
    if not collaborator.is_active:
        raise AuthenticationError("Account deactivated. Contact management.")

    # Step 4 — generate and store token
    _write_session_file(_generate_token(collaborator))

    # Step 5 — return collaborator regardless of must_change_password
    return collaborator


def logout() -> None:
    """
    End the current session by deleting the session file.

    Safe to call even if no session exists.
    """
    _delete_session_file()


def get_session_user(session: Session) -> Collaborator | None:
    """
    Return the currently authenticated collaborator from the session token.

    Reads the session file, validates the JWT, and loads the collaborator
    from the database. Returns None if no valid session exists.

    Args:
        session: SQLAlchemy database session.

    Returns:
        Collaborator | None: The authenticated collaborator, or None if
                             no valid session exists.

    Raises:
        AuthenticationError: If the token is expired or invalid.
    """
    token = _read_session_file()
    if not token:
        return None

    payload = _decode_token(token)

    collaborator: Collaborator | None = session.get(Collaborator, payload["user_id"])

    if not collaborator:
        _delete_session_file()
        raise AuthenticationError("Session user no longer exists.")

    if not collaborator.is_active:
        _delete_session_file()
        raise AuthenticationError("Account deactivated. Contact management.")

    return collaborator


def change_password(
    session: Session,
    collaborator: Collaborator,
    current_password: str,
    new_password: str,
) -> None:
    """
    Change a collaborator's password.

    Verifies the current password, ensures the new one differs, hashes
    and saves the new password.

    Args:
        session: SQLAlchemy database session.
        collaborator: The Collaborator whose password is being changed.
        current_password: The current plaintext password to verify.
        new_password: The new plaintext password to set.

    Raises:
        AuthenticationError: If the current password is wrong.
        ValidationError: If the new password matches the current one.
    """
    if not collaborator.verify_password(current_password):
        raise AuthenticationError("Current password is incorrect.")

    if collaborator.verify_password(new_password):
        raise ValidationError("New password must differ from your current password.")

    validate_password(new_password)
    collaborator.set_password(new_password)
    session.commit()


def complete_first_login(session: Session, collaborator: Collaborator) -> None:
    """Clear the must_change_password flag after a successful first-login change.

    Called by the view layer after change_password() succeeds on first login.
    Marks the collaborator's account as fully activated.

    Args:
        session: SQLAlchemy database session.
        collaborator: The Collaborator completing their first login.
    """
    collaborator.must_change_password = False
    session.commit()
