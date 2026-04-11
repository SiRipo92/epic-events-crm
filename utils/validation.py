"""
Shared validation utilities.

These helpers are called by service functions before writing to the
database. They raise ValidationError on invalid input.
"""

from __future__ import annotations

import re
from datetime import datetime

from exceptions import ValidationError

# ---- For Clients and Collaborators


def validate_password(password: str) -> None:
    """Validate that a password meets minimum security requirements.

    Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit

    Args:
        password: The plaintext password to validate.

    Raises:
        ValidationError: If the password does not meet requirements.
    """
    if not password or len(password) < 8:
        raise ValidationError(
            "Password must be at least 8 characters long."
        )
    if not any(c.isupper() for c in password):
        raise ValidationError(
            "Password must contain at least one uppercase letter."
        )
    if not any(c.islower() for c in password):
        raise ValidationError(
            "Password must contain at least one lowercase letter."
        )
    if not any(c.isdigit() for c in password):
        raise ValidationError(
            "Password must contain at least one digit."
        )


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
        raise ValidationError(f"'{email}' is not a valid email address.")


# ---- For Events


def validate_location(
    location_street: str | None,
    location_city: str | None,
    location_zip: str | None,
) -> None:
    """Validate that required location fields are provided.

    Args:
        location_street: Street address.
        location_city: City name.
        location_zip: Postal code.

    Raises:
        ValidationError: If any required location field is missing.
    """
    missing = []
    if not location_street:
        missing.append("location_street")
    if not location_city:
        missing.append("location_city")
    if not location_zip:
        missing.append("location_zip")

    if missing:
        raise ValidationError(
            f"Missing required location fields: {', '.join(missing)}."
        )


def validate_event_dates(start_date: datetime, end_date: datetime) -> None:
    """Validate that event start date is before end date.

    Args:
        start_date: Event start datetime.
        end_date: Event end datetime.

    Raises:
        ValidationError: If start_date is not before end_date.
    """
    if start_date >= end_date:
        raise ValidationError("Event start date must be before end date.")
