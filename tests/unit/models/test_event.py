"""
Unit tests for the Event ORM model.

Tests cover:
    - has_support computed property
    - duration_hours computed property
    - is_past computed property
"""

from datetime import datetime

import pytest


class TestEventHasSupport:
    """Tests for the has_support computed property.

    Happy path:  support_id is set.
    Sad path:    support_id is None.
    """

    def test_has_support_when_assigned(self, event_with_support):
        """Happy path: event with support_id set returns True."""
        assert event_with_support.has_support is True

    def test_no_support_when_support_id_is_none(self, event_without_support):
        """Sad path: event with support_id None returns False."""
        assert event_without_support.has_support is False


class TestEventDurationHours:
    """Tests for the duration_hours computed property.

    Happy path:  standard duration.
    Edge cases:  midnight crossing, zero duration, fractional hours.
    """

    @pytest.mark.parametrize(
        "start, end, expected",
        [
            (datetime(2025, 9, 1, 9, 0), datetime(2025, 9, 1, 17, 0), 8.0),
            (datetime(2025, 9, 1, 18, 0), datetime(2025, 9, 1, 19, 30), 1.5),
            (datetime(2025, 9, 1, 22, 0), datetime(2025, 9, 2, 2, 0), 4.0),
            (datetime(2025, 9, 1, 12, 0), datetime(2025, 9, 1, 12, 0), 0.0),
        ],
    )
    def test_duration_hours(self, event_without_support, start, end, expected):
        """Parametrized: duration_hours returns correct value for all scenarios."""
        event_without_support.start_date = start
        event_without_support.end_date = end
        assert event_without_support.duration_hours == expected


class TestEventIsPast:
    """Tests for the is_past computed property.

    Happy path:  event ended in the past.
    Sad path:    event ends in the future.
    """

    def test_past_event_is_past(self, past_event):
        """Happy path: event that ended yesterday returns True."""
        assert past_event.is_past is True

    def test_future_event_is_not_past(self, future_event):
        """Sad path: event ending tomorrow returns False."""
        assert future_event.is_past is False


class TestEventLocation:
    """Tests for the location computed property."""

    def test_full_address(self, make_event):
        """Return formatted full address from all four fields."""
        e = make_event(
            location_street="34 rue de Albatross",
            location_zip="92000",
            location_city="Nanterre",
            location_country="France",
        )
        assert e.location == "34 rue de Albatross, 92000 Nanterre, France"

    def test_partial_address_no_street(self, make_event):
        """Return partial address when street is missing."""
        e = make_event(
            location_zip="92000",
            location_city="Nanterre",
            location_country="France",
        )
        assert e.location == "92000 Nanterre, France"

    def test_city_only(self, make_event):
        """Return city name alone when only city is set."""
        e = make_event(location_city="Paris")
        assert e.location == "Paris"

    def test_no_location_returns_none(self, make_event):
        """Return None when no location fields are set."""
        e = make_event()
        assert e.location is None
