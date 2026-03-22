"""
Unit tests for the Client ORM model.

Tests cover:
    - full_name computed property
    - full_name_formal computed property
    - has_active_support computed property
"""

import pytest
from unittest.mock import MagicMock

class TestClientFullName:
    """Tests for full_name computed property.

    Happy paths:  standard names.
    Edge cases:   compound last names.
    """

    def test_full_name_standard(self, prospect_client):
        """Happy path: first + last in display format."""
        prospect_client.first_name = "Jean"
        prospect_client.last_name = "Durand"
        assert prospect_client.full_name == "Jean Durand"

    @pytest.mark.parametrize("first, last, expected", [
        ("Jean", "Durand", "Jean Durand"),
        ("Marie", "Leclerc", "Marie Leclerc"),
        ("Anne", "de la Rue", "Anne de la Rue"),  # edge: compound name
    ])
    def test_full_name(self, prospect_client, first, last, expected):
        """Parametrized: full_name returns first + last in display format."""
        prospect_client.first_name = first
        prospect_client.last_name = last
        assert prospect_client.full_name == expected

    @pytest.mark.parametrize("first, last, expected", [
        ("Jean", "Durand", "DURAND, Jean"),
        ("Marie", "Leclerc", "LECLERC, Marie"),
        ("Anne", "de la Rue", "DE LA RUE, Anne"),  # edge: compound name
    ])
    def test_full_name_formal(self, prospect_client, first, last, expected):
        """Parametrized: full_name_formal returns LAST, First format."""
        prospect_client.first_name = first
        prospect_client.last_name = last
        assert prospect_client.full_name_formal == expected


class TestClientHasActiveSupport:
    """Tests for the has_active_support computed property.

    Happy paths:  at least one event has support assigned.
    Sad paths:    no contracts, no events, events with no support.
    """

    def _make_contract_with_event(self, support_id):
        """Helper: mock contract whose event has the given support_id."""
        event = MagicMock()
        event.support_id = support_id
        contract = MagicMock()
        contract.event = event
        return contract

    def _make_contract_without_event(self):
        """Helper: mock contract with no linked event."""
        contract = MagicMock()
        contract.event = None
        return contract

    def test_has_support_when_event_assigned(self, prospect_client):
        """Happy path: one event with support returns True."""
        prospect_client.contracts = [
            self._make_contract_with_event(support_id=1)
        ]
        assert prospect_client.has_active_support is True

    def test_no_support_when_no_contracts(self, prospect_client):
        """Sad path: no contracts returns False."""
        prospect_client.contracts = []
        assert prospect_client.has_active_support is False

    def test_no_support_when_no_events(self, prospect_client):
        """Sad path: contracts exist but no events returns False."""
        prospect_client.contracts = [
            self._make_contract_without_event()
        ]
        assert prospect_client.has_active_support is False

    def test_no_support_when_support_id_none(self, prospect_client):
        """Sad path: event exists but support_id is None returns False."""
        prospect_client.contracts = [
            self._make_contract_with_event(support_id=None)
        ]
        assert prospect_client.has_active_support is False
