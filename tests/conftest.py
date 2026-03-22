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

from models.client import Client, ClientStatus
from models.contract import Contract, ContractStatus
from models.event import Event



# ── Factory fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def make_contract():
    """Factory for Contract instances.

    Usage:
        def test_something(make_contract):
            c = make_contract(status=ContractStatus.SIGNED)
    """
    def _factory(
        id=1,
        client_id=1,
        commercial_id=1,
        total_amount=Decimal("5000.00"),
        remaining_amount=Decimal("5000.00"),
        status=ContractStatus.DRAFT,
    ):
        c = Contract()
        c.id = id
        c.client_id = client_id
        c.commercial_id = commercial_id
        c.total_amount = total_amount
        c.remaining_amount = remaining_amount
        c.status = status
        return c
    return _factory


@pytest.fixture
def make_event():
    """Factory for Event instances.

    Usage:
        def test_something(make_event):
            e = make_event(support_id=3)
    """
    def _factory(
        id=1,
        contract_id=1,
        title="Test Event",
        start_date=None,
        end_date=None,
        support_id=None,
        is_cancelled=False,
    ):
        e = Event()
        e.id = id
        e.contract_id = contract_id
        e.title = title
        e.start_date = start_date or datetime(2025, 9, 1, 9, 0)
        e.end_date = end_date or datetime(2025, 9, 1, 17, 0)
        e.support_id = support_id
        e.is_cancelled = is_cancelled
        return e
    return _factory


@pytest.fixture
def make_client():
    """Factory for Client instances.

    Usage:
        def test_something(make_client):
            c = make_client(status=ClientStatus.ACTIVE)
    """
    def _factory(
        id=1,
        first_name="Jean",
        last_name="Durand",
        email="jean@company.com",
        commercial_id=1,
        status=ClientStatus.PROSPECT,
        contracts=None,
    ):
        c = Client()
        c.id = id
        c.first_name = first_name
        c.last_name = last_name
        c.email = email
        c.commercial_id = commercial_id
        c.status = status
        c.contracts = contracts if contracts is not None else []
        return c
    return _factory


# ── Named contract fixtures ───────────────────────────────────────────────────

@pytest.fixture
def draft_contract(make_contract):
    """A contract in DRAFT status — cannot create events against it."""
    return make_contract(id=1, status=ContractStatus.DRAFT)


@pytest.fixture
def pending_contract(make_contract):
    """A contract in PENDING status — awaiting client signature."""
    return make_contract(id=2, status=ContractStatus.PENDING)


@pytest.fixture
def signed_contract(make_contract):
    """A contract in SIGNED status — events can be created against it."""
    return make_contract(
        id=3, status=ContractStatus.SIGNED,
        remaining_amount=Decimal("2500.00")
    )


@pytest.fixture
def completed_contract(make_contract):
    """A contract in COMPLETED status — fully paid and delivered."""
    return make_contract(
        id=4, status=ContractStatus.COMPLETED,
        remaining_amount=Decimal("0.00")
    )


@pytest.fixture
def cancelled_contract(make_contract):
    """A contract in CANCELLED status — no further actions possible."""
    return make_contract(
        id=5, status=ContractStatus.CANCELLED,
        total_amount=Decimal("3000.00"),
        remaining_amount=Decimal("3000.00")
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


# ── Named client fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def prospect_client(make_client):
    """A freshly created client — PROSPECT status, no contracts."""
    return make_client(id=1, status=ClientStatus.PROSPECT)


@pytest.fixture
def active_client(make_client):
    """A client with a signed contract — ACTIVE status."""
    return make_client(
        id=2, first_name="Marie", last_name="Leclerc",
        email="marie@company.com", status=ClientStatus.ACTIVE
    )
