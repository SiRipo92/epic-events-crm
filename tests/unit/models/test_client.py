"""
Unit tests for the Client ORM model.

Tests cover:
    - full_name computed property
    - full_name_formal computed property
    - has_active_support computed property
"""

import pytest


class TestClientFullName:
    """Tests for full_name computed property.

    Happy paths:  standard names.
    Edge cases:   compound last names.
    """

    def test_full_name_standard(self, client):
        """Happy path: first + last in display format."""
        client.first_name = "Jean"
        client.last_name = "Durand"
        assert client.full_name == "Jean Durand"

    @pytest.mark.parametrize("first, last, expected", [
        ("Jean", "Durand", "Jean Durand"),
        ("Marie", "Leclerc", "Marie Leclerc"),
        ("Anne", "de la Rue", "Anne de la Rue"),  # edge: compound name
    ])
    def test_full_name(self, client, first, last, expected):
        """Parametrized: full_name returns first + last in display format."""
        client.first_name = first
        client.last_name = last
        assert client.full_name == expected

    @pytest.mark.parametrize("first, last, expected", [
        ("Jean", "Durand", "DURAND, Jean"),
        ("Marie", "Leclerc", "LECLERC, Marie"),
        ("Anne", "de la Rue", "DE LA RUE, Anne"),  # edge: compound name
    ])
    def test_full_name_formal(self, client, first, last, expected):
        """Parametrized: full_name_formal returns LAST, First format."""
        client.first_name = first
        client.last_name = last
        assert client.full_name_formal == expected


class TestClientHasActiveSupport:
    """Tests for the has_active_support computed property.

    Happy paths:  at least one event has support assigned.
    Sad paths:    no contracts, no events, events with no support.
    """

    def test_has_support_when_event_assigned(self, client_with_active_support):
        """Happy path: one event with support returns True."""
        assert client_with_active_support.has_active_support is True

    def test_no_support_when_no_contracts(self, client_without_contracts):
        """Sad path: no contracts returns False."""
        assert client_without_contracts.has_active_support is False

    def test_no_support_when_no_events(self, client_with_contract):
        """Sad path: contracts exist but no events returns False."""
        # draft_contract has no `event` attached
        assert client_with_contract.has_active_support is False

    def test_no_support_when_support_id_none(self, client_with_event_no_support):
        """Sad path: event exists but support_id is None returns False."""
        assert client_with_event_no_support.has_active_support is False
