"""
Shared pytest fixtures for the Epic Events CRM test suite.

Sprint 1 scope: Client, Contract, Event model unit tests only.
Collaborator fixtures and DB session fixtures added in Sprint 2.

Fixtures are organised as:
    - Factory fixtures: return a callable that builds model instances
    - Named fixtures: call factories with specific preset values
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from models.client import Client
from models.contract import Contract, ContractStatus
from models.event import Event



# ── Factory fixtures ──────────────────────────────────────────────────────────
@pytest.fixture
def make_client():
    """Factory for Client instances.

    Usage:
    def test_something(make_client):
        c = make_client(first_name="Marie", commercial_id=2)
    """
    def _factory(
        id: int = 1,
        first_name: str = "Jean",
        last_name: str = "Durand",
        email: str = "jean@company.com",
        commercial_id: int = 1,
        contracts: list | None = None,
    ) -> Client:
        c = Client()
        c.id = id
        c.first_name = first_name
        c.last_name = last_name
        c.email = email
        c.commercial_id = commercial_id
        c.contracts = contracts if contracts is not None else []
        return c
    return _factory


@pytest.fixture
def make_contract():
    """Factory for Contract instances."""
    def _factory(
        id=1,
        client_id=1,
        commercial_id=1,
        total_amount=Decimal("5000.00"),
        remaining_amount=Decimal("5000.00"),
        deposit_received=False,
        status: ContractStatus = ContractStatus.DRAFT,
    ):
        c = Contract()
        c.id = id
        c.client_id = client_id
        c.commercial_id = commercial_id
        c.total_amount = total_amount
        c.remaining_amount = remaining_amount
        c.deposit_received = deposit_received
        c.status = status
        return c
    return _factory

@pytest.fixture
def make_event():
    """Factory for Event instances."""

    def _factory(
        id: int = 1,
        contract_id: int = 1,
        title: str = "Test Event",
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        location_street: str | None = None,
        location_zip: str | None = None,
        location_city: str | None = None,
        location_country: str | None = None,
        attendees: int = 0,
        notes: str | None = None,
        support_id: int | None = None,
        is_cancelled: bool = False,
    ):
        e = Event()
        e.id = id
        e.contract_id = contract_id
        e.title = title
        e.start_date = start_date or datetime(2025, 9, 1, 9, 0)
        e.end_date = end_date or datetime(2025, 9, 1, 17, 0)
        e.location_street = location_street
        e.location_zip = location_zip
        e.location_city = location_city
        e.location_country = location_country
        e.attendees = attendees
        e.notes = notes
        e.support_id = support_id
        e.is_cancelled = is_cancelled
        return e
    return _factory

# ── Named client fixtures ───────────────────────────────────────────────────

@pytest.fixture
def client(make_client):
    """Base client with no contracts (neutral state)."""
    return make_client(
        id=1,
        first_name="Jean",
        last_name="Durand",
        email="jean.durand@epicevents.com",
        commercial_id=1,
        contracts=[],
    )


@pytest.fixture
def client_without_contracts(client):
    """Client with no contracts (initial state)."""
    client.contracts = []
    return client


@pytest.fixture
def client_with_contract(client, draft_contract):
    """Client linked to a single contract."""
    client.contracts = [draft_contract]
    return client


@pytest.fixture
def client_with_event_no_support(client, signed_contract, event_without_support):
    """Client with contract → event but no support assigned."""
    signed_contract.event = event_without_support
    client.contracts = [signed_contract]
    return client


@pytest.fixture
def client_with_active_support(client, signed_contract, event_with_support):
    """Client with at least one event having support assigned."""
    signed_contract.event = event_with_support
    client.contracts = [signed_contract]
    return client


@pytest.fixture
def client_with_event_but_no_support(client, signed_contract, event_without_support):
    """Client with event but no support assigned (explicit case)."""
    signed_contract.event = event_without_support
    client.contracts = [signed_contract]
    return client


# ── Named contract fixtures ───────────────────────────────────────────────────

@pytest.fixture
def draft_contract(make_contract):
    """DRAFT — initial state, editable."""
    return make_contract(
        id=1,
        status=ContractStatus.DRAFT,
        total_amount=Decimal("3000.00"),
        remaining_amount=Decimal("3000.00"),
    )


@pytest.fixture
def pending_contract(make_contract):
    """PENDING — sent to client, awaiting signature."""
    return make_contract(
        id=2,
        status=ContractStatus.PENDING,
        total_amount=Decimal("3000.00"),
        remaining_amount=Decimal("3000.00"),
    )


@pytest.fixture
def signed_contract(make_contract):
    """SIGNED — signed but no deposit yet."""
    return make_contract(
        id=3,
        status=ContractStatus.SIGNED,
        total_amount=Decimal("3000.00"),
        remaining_amount=Decimal("3000.00"),
    )


@pytest.fixture
def deposit_received_contract(make_contract):
    """DEPOSIT_RECEIVED — event creation unlocked."""
    return make_contract(
        id=4,
        status=ContractStatus.DEPOSIT_RECEIVED,
        total_amount=Decimal("3000.00"),
        remaining_amount=Decimal("2000.00"),
        deposit_received=True,
    )


@pytest.fixture
def paid_contract(make_contract):
    """PAID_IN_FULL — fully paid."""
    return make_contract(
        id=5,
        status=ContractStatus.PAID_IN_FULL,
        total_amount=Decimal("3000.00"),
        remaining_amount=Decimal("0.00"),
        deposit_received=True,
    )


@pytest.fixture
def cancelled_contract(make_contract):
    """CANCELLED — terminal state."""
    return make_contract(
        id=6,
        status=ContractStatus.CANCELLED,
        total_amount=Decimal("3000.00"),
        remaining_amount=Decimal("3000.00"),
    )


# ── Named event fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def event_without_support(make_event):
    """An event with no support assigned."""
    return make_event(
        id=1, title="Annual Gala",
        start_date=datetime(2025, 9, 1, 18, 0),
        end_date=datetime(2025, 9, 1, 23, 0)
    )


@pytest.fixture
def event_with_support(make_event):
    """An event with support_id set."""
    return make_event(
        id=2, title="Product Launch",
        start_date=datetime(2025, 10, 15, 9, 0),
        end_date=datetime(2025, 10, 15, 17, 0),
        support_id=1
    )


@pytest.fixture
def eight_hour_event(make_event):
    """An event with exactly 8 hours duration."""
    return make_event(
        id=3, title="Workshop",
        start_date=datetime(2025, 11, 1, 9, 0),
        end_date=datetime(2025, 11, 1, 17, 0)
    )


@pytest.fixture
def past_event(make_event):
    """An event that ended yesterday — is_past returns True."""
    return make_event(
        id=4, title="Past Conference",
        start_date=datetime.now(timezone.utc) - timedelta(days=2),
        end_date=datetime.now(timezone.utc) - timedelta(days=1)
    )


@pytest.fixture
def future_event(make_event):
    """An event starting tomorrow — is_past returns False."""
    return make_event(
        id=5, title="Upcoming Gala",
        start_date=datetime.now(timezone.utc) + timedelta(days=1),
        end_date=datetime.now(timezone.utc) + timedelta(days=2)
    )
