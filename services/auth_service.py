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

import jwt

from config import settings
from exceptions import AuthenticationError, MustChangePasswordError, ValidationError

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
