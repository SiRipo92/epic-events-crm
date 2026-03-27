"""
Authentication service.

Handles login, logout, session token management, and current user
resolution. All authentication logic lives here — never in the CLI
or view layer.

Session tokens are JWT tokens stored at ~/.epic_events/session
with chmod 600. They expire after 8 hours.
"""

from datetime import datetime, timedelta, timezone

import jwt

from config import settings
from exceptions import AuthenticationError

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
