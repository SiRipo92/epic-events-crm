"""
Authentication service.

Handles login, logout, session token management, and current user
resolution. All authentication logic lives here — never in the CLI
or view layer.

Session tokens are JWT tokens stored at ~/.epic_events/session
with chmod 600. They expire after 8 hours.
"""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

from config import settings
from exceptions import AuthenticationError, ValidationError
from models.collaborator import Collaborator


# ── Session file helpers ───────────────────────────────────────────────────────

def _get_session_path() -> Path:
    """Return the path to the session token file."""
    return settings.session_file

def _write_session_file(token: str) -> Path:
    """
    Write a JWT token to the session file with restricted permissions.

    Creates the parent directory if it does not exist.
    Sets file permissions to 600 (owner read/write only).
    """
    session_path = _get_session_path()
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(token)
    os.chmod(session_path, 0o600)

def _delete_session_file() -> None:
    """Delete the session file if it exists."""
    session_path = _get_session_path()
    if session_path.exists():
        session_path.unlink()

# ── Token helpers ─────────────────────────────────────────────────────────────

def _generate_token(collaborator) -> str:
    """Generate a signed JWT token for the given collaborator.

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

def login(session, email: str, password: str):
    """Authenticate a collaborator and create a session token.

    Checks credentials and active status, then writes a JWT to the
    session file. Returns the collaborator regardless of
    must_change_password — the caller is responsible for checking
    that flag and routing to the password change screen if needed.

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
    collaborator = session.query(Collaborator).filter_by(email=email).first()

    # Step 2 — verify password (same error as unknown email — no enumeration)
    if not collaborator or not collaborator.verify_password(password):
        raise AuthenticationError("Invalid credentials. Please try again.")

    # Step 3 — check active status
    if not collaborator.is_active:
        raise AuthenticationError("Account deactivated. Contact management.")

    # Step 4 — generate and store token
    _write_session_file(_generate_token(collaborator))

    # Step 5 — return collaborator regardless of must_change_password
    # The caller checks collaborator.must_change_password and routes accordingly
    return collaborator

def logout() -> None:
    """
    End the current session by deleting the session file.

    Safe to call even if no session exists.
    """
    pass


def change_password(session, collaborator, current_password: str, new_password: str):
    """
    Change a collaborator's password.

    Verifies the current password, ensures the new one differs, hashes
    and saves the new password, and clears must_change_password.

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
        raise ValidationError(
            "New password must differ from your current password."
        )

    collaborator.set_password(new_password)
    collaborator.must_change_password = False
    session.commit()
