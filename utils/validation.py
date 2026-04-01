"""
Shared validation utilities.

These helpers are called by service functions before writing to the
database. They raise ValidationError on invalid input.
"""

from __future__ import annotations

import re

from exceptions import ValidationError


def validate_email(email: str) -> None:
    """Validate that an email address has a minimally correct format.

    Checks for presence of @ and a dot in the domain portion.
    Does not perform DNS lookup or full RFC 5322 validation.

    Args:
        email: The email string to validate.

    Raises:
        ValidationError: If the email format is invalid or empty.
    """
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not email or not re.match(pattern, email.strip()):
        raise ValidationError(
            f"'{email}' is not a valid email address."
        )
