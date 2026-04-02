"""Unit tests for shared validation utilities."""

import pytest
from datetime import datetime

from exceptions import ValidationError
from utils.validation import validate_email, validate_event_dates, validate_location


class TestValidateEmail:
    """Tests for validate_email()."""

    def test_valid_email_passes(self):
        """Valid email raises no error."""
        validate_email("test@example.com")

    @pytest.mark.parametrize("email", [
        "notanemail",
        "missing@nodot",
        "",
        "   ",
        "@nodomain.com",
    ])
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

    @pytest.mark.parametrize("street,city,zip_code", [
        (None, "Paris", "75001"),
        ("34 rue de la Paix", None, "75001"),
        ("34 rue de la Paix", "Paris", None),
        (None, None, None),
    ])
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
