"""
Unit tests for the Event ORM model.

Tests cover:
    - has_support() domain method
    - duration_hours() domain method
    - is_past computed property
"""

import pytest
from datetime import datetime

from models.event import Event


class TestEventHasSupport:
    """Tests for the has_support() domain method.

    Happy path:  support_id is set.
    Sad path:    support_id is None.
    """

    def test_has_support_when_assigned(self, event_with_support):
        """Happy path: event with support_id set returns True."""
        assert event_with_support.has_support() is True

    def test_no_support_when_support_id_is_none(self, event_without_support):
        """Sad path: event with support_id None returns False."""
        assert event_without_support.has_support() is False


class TestEventDurationHours:
    """Tests for the duration_hours() domain method.

    Happy path:  standard duration.
    Edge cases:  midnight crossing, zero duration, fractional hours.
    """

    @pytest.mark.parametrize("start, end, expected", [
        (datetime(2025, 9, 1,  9,  0), datetime(2025, 9, 1, 17,  0), 8.0),
        (datetime(2025, 9, 1, 18,  0), datetime(2025, 9, 1, 19, 30), 1.5),
        (datetime(2025, 9, 1, 22,  0), datetime(2025, 9, 2,  2,  0), 4.0),
        (datetime(2025, 9, 1, 12,  0), datetime(2025, 9, 1, 12,  0), 0.0),
    ])
    def test_duration_hours(self, event_without_support, start, end, expected):
        """Parametrized: duration_hours returns correct value for all scenarios."""
        event_without_support.start_date = start
        event_without_support.end_date = end
        assert event_without_support.duration_hours() == expected


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
