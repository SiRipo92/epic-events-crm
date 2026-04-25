"""Unit tests for shared validation utilities."""

from datetime import datetime

import pytest

from utils.exceptions import ValidationError
from utils.validation import (
    validate_email,
    validate_event_dates,
    validate_location,
    validate_password,
    validate_phone,
)


class TestValidateEmail:
    """Tests for validate_email()."""

    def test_valid_email_passes(self):
        """Valid email raises no error."""
        validate_email("test@example.com")

    @pytest.mark.parametrize(
        "email",
        [
            "notanemail",
            "missing@nodot",
            "",
            "   ",
            "@nodomain.com",
        ],
    )
    def test_invalid_email_raises(self, email):
        """Invalid email format raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_email(email)


class TestValidateLocation:
    """Tests for validate_location()."""

    def test_valid_location_passes(self):
        """All required fields provided raises no error."""
        validate_location(
            location_street="34 rue de la Paix",
            location_city="Paris",
            location_zip="75001",
        )

    @pytest.mark.parametrize(
        "street,city,zip_code",
        [
            (None, "Paris", "75001"),
            ("34 rue de la Paix", None, "75001"),
            ("34 rue de la Paix", "Paris", None),
            (None, None, None),
        ],
    )
    def test_missing_location_field_raises(self, street, city, zip_code):
        """Missing any required location field raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_location(street, city, zip_code)


class TestValidateEventDates:
    """Tests for validate_event_dates()."""

    def test_valid_dates_pass(self):
        """start_date before end_date raises no error."""
        validate_event_dates(
            start_date=datetime(2025, 9, 1, 9, 0),
            end_date=datetime(2025, 9, 1, 17, 0),
        )

    def test_start_after_end_raises(self):
        """start_date after end_date raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_event_dates(
                start_date=datetime(2025, 9, 1, 17, 0),
                end_date=datetime(2025, 9, 1, 9, 0),
            )

    def test_start_equal_to_end_raises(self):
        """start_date equal to end_date raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_event_dates(
                start_date=datetime(2025, 9, 1, 9, 0),
                end_date=datetime(2025, 9, 1, 9, 0),
            )


class TestValidatePassword:
    """Tests for validate_password()."""

    def test_valid_password_passes(self):
        """Strong password raises no error."""
        validate_password("Secure123")

    @pytest.mark.parametrize(
        "password",
        [
            "short1A",  # too short
            "alllowercase1",  # no uppercase
            "ALLUPPERCASE1",  # no lowercase
            "NoDigitsHere",  # no digit
            "",  # empty
        ],
    )
    def test_weak_password_raises(self, password):
        """Weak password raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_password(password)


class TestValidatePhone:
    """Tests for validate_phone()."""

    @pytest.mark.parametrize(
        "phone",
        [
            "0612345678",
            "+33612345678",
            "06 12 34 56 78",
        ],
    )
    def test_valid_phone_passes(self, phone):
        """Valid French phone number raises no error."""
        validate_phone(phone)

    @pytest.mark.parametrize(
        "phone",
        [
            "123",
            "abcdefghij",
            "",
            "0012345678",
        ],
    )
    def test_invalid_phone_raises(self, phone):
        """Invalid phone raises ValidationError."""
        with pytest.raises(ValidationError):
            validate_phone(phone)
