# Epic Events CRM

> A secure command-line CRM for managing clients, contracts, and events
> across three operational departments: Management, Commercial, and Support.

Built with Python · PostgreSQL · SQLAlchemy · Typer · Rich · bcrypt · PyJWT · Sentry

[![CI](https://github.com/SiRipo92/epic-events-crm/actions/workflows/ci.yml/badge.svg)](https://github.com/SiRipo92/epic-events-crm/actions/workflows/ci.yml)
[![Coverage](./docs/badges/coverage.svg)](https://github.com/SiRipo92/epic-events-crm/actions/workflows/ci.yml)
[![Linting: flake8](https://img.shields.io/badge/linting-flake8-blue)](https://flake8.pycqa.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)

---

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Database Setup](#database-setup)
- [Running the App](#running-the-app)
- [Navigation](#navigation)
- [Testing](#testing)
- [Linting & Code Quality](#linting--code-quality)
- [Project Structure](#project-structure)
- [Sentry Setup](#sentry-setup)
- [Security](#security)
- [Contributing](#contributing)

---

## Project Overview

Epic Events is an event management company (parties, professional meetings,
outdoor events). This CRM replaces disconnected Excel sheets with a unified
CLI platform that enforces **role-based access** and logs all errors to
**Sentry**.

**Three departments, three roles:**

| Role | Key Abilities |
|---|---|
| Management | Full control over collaborators and all contracts; assign support to events |
| Commercial | Create and manage own clients; create events for deposit-received contracts |
| Support | View and update events assigned to them |

**CRM Operations Flow:**

![CRM Operations Flow](docs/crm_flow.png)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy 2.x |
| Migrations | Alembic |
| CLI framework | Typer |
| Terminal output | Rich |
| Password hashing | bcrypt (cost factor 12) |
| Session tokens | PyJWT (8h expiry) |
| Error monitoring | Sentry SDK |
| Config | python-dotenv |
| Testing | pytest + pytest-cov |

---

## Prerequisites

- Python 3.9 or higher (3.11 recommended)
- PostgreSQL 17 installed and running locally
- pgAdmin 4 (bundled with the PostgreSQL installer)
- `pip` and `venv`

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/SiRipo92/epic-events-crm.git
cd epic-events-crm

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # macOS / Linux
.venv\Scripts\activate          # Windows

# 3. Install production dependencies
pip install -r requirements.txt

# 4. Install dev dependencies (testing, linting, seed data)
pip install -r requirements-dev.txt
```

---

## Environment Setup

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

`.env.example` (committed to Git — keys only, no values):

```env
DATABASE_URL=
TEST_DATABASE_URL=
SECRET_KEY=
SENTRY_DSN=
```

Your `.env` (never committed — fill in your actual values):

```env
DATABASE_URL=postgresql://epic_events_user:your_password@localhost/epic_events_db
TEST_DATABASE_URL=postgresql://epic_events_user:your_password@localhost/epic_events_test
SECRET_KEY=your_generated_secret_key
SENTRY_DSN=https://your-key@sentry.io/your-project-id
```

To generate a secure `SECRET_KEY`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> Never commit your `.env` file. It is listed in `.gitignore`.
> Only `.env.example` is committed.

---

## Database Setup

### 1. Create the app user and databases

Open pgAdmin → select your server → Tools → Query Tool, then run:

```sql
-- Application database
CREATE USER epic_events_user WITH PASSWORD 'your_password';
CREATE DATABASE epic_events_db OWNER epic_events_user;

-- Test database (used by the integration test suite)
CREATE DATABASE epic_events_test OWNER epic_events_user;

GRANT CONNECT ON DATABASE epic_events_db TO epic_events_user;
GRANT USAGE ON SCHEMA public TO epic_events_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO epic_events_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO epic_events_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO epic_events_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO epic_events_user;
```

### 2. Run Alembic migrations

Apply the full schema to both databases:

```bash
# Apply to the application database
alembic upgrade head

# Apply to the test database
DATABASE_URL=$TEST_DATABASE_URL alembic upgrade head
```

This creates all tables and seeds the three roles (`MANAGEMENT`, `COMMERCIAL`,
`SUPPORT`) automatically.

### 3. Create the first Management account

A fresh database has no collaborators. Create the first management-role account
using the seed script:

```bash
python -m cli.commands.seed_admin
```

You will be prompted for a name, email, and temporary password. This account
will be forced to change its password on first login. All subsequent
collaborator accounts (Commercial, Support) are created from within the app
by a logged-in Management user.

### 4. Verify connection

```bash
python -c "
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
load_dotenv()
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    print('Connected:', conn.execute(text('SELECT 1')).fetchone())
"
```

### 5. Creating a new migration (after model changes)

```bash
# Auto-generate a migration from model diffs
alembic revision --autogenerate -m "describe your change here"

# Review the generated file in migrations/versions/, then apply
alembic upgrade head

# Other useful Alembic commands
alembic current          # Show which revision the DB is currently at
alembic history --verbose  # Show full migration history
alembic downgrade -1     # Roll back the last migration
```

---

## Running the App

```bash
python main.py
```

That is the only command you need. The app detects your session state and
routes automatically:

- Valid session exists → main menu shown immediately
- No session or expired token → login prompt shown, then menu
- First login → password change screen shown before menu

No subcommands are required from the user.

---

## Navigation

The app is menu-driven. After login, you see a role-scoped menu:

**Management**
```
[1] Clients
[2] Contracts
[3] Events
[4] Collaborators
[0] Logout
```

**Commercial**
```
[1] Clients
[2] Contracts
[3] Events
[0] Logout
```

**Support**
```
[1] Clients
[2] Contracts
[3] Events → includes "My Events" filter
[0] Logout
```

Each menu option leads to a sub-menu with the actions available to that role.
All navigation is number-based — no commands to memorise.

---

## Testing

The test suite is structured in three layers:

| Layer | Location | What it tests |
|---|---|---|
| Unit | `tests/unit/` | Model methods and decorators — no DB required |
| Integration | `tests/integration/` | Services against a real test DB (`epic_events_test`) |
| Functional | `tests/functional/` | Full CLI stack via Typer's test runner |

Each integration test runs inside a transaction that is rolled back on
teardown — no data persists between tests.

```bash
# Run the full test suite
pytest

# Run with coverage report
pytest --cov=. --cov-report=term-missing

# Fail if coverage drops below 80%
pytest --cov=. --cov-fail-under=80

# Run a specific layer
pytest tests/unit/
pytest tests/integration/
pytest tests/functional/

# Run a specific file
pytest tests/unit/models/test_collaborator.py -v

# Makefile shortcuts
make test        # pytest (full suite)
make coverage    # pytest --cov=. --cov-report=term-missing
```

Coverage target: **80% minimum** (enforced in CI).

> **Note:** Integration tests require `TEST_DATABASE_URL` to be set in your
> `.env` and the `epic_events_test` database to exist with migrations applied.

---

## Linting & Code Quality

The project enforces PEP8 compliance via **flake8** and consistent formatting
via **black** and **isort**. Configuration lives in `setup.cfg` (flake8) and
`pyproject.toml` (black, isort, coverage).

```bash
# Apply isort + black formatting in-place
make format

# Check flake8 compliance (no changes — exits non-zero on violations)
make lint

# Run both checks (same as CI)
make check
```

Running `make check` before every push is the pre-push contract for this
project. CI will fail if either check does not pass.

**Flake8 config** (`setup.cfg`):

```ini
[flake8]
max-line-length = 119
exclude = .git,__pycache__,.venv,migrations/versions
```

---

## Project Structure

```
epic-events-crm/
│
├── main.py                        # Entry point — calls run_app()
│
├── models/
│   ├── __init__.py                # Re-exports all models
│   ├── base.py                    # DeclarativeBase only
│   ├── role.py                    # Role table (MANAGEMENT/COMMERCIAL/SUPPORT)
│   ├── collaborator.py            # Collaborator ORM class
│   ├── client.py                  # FK: commercial_id → collaborators.id
│   ├── contract.py                # FK: commercial_id → collaborators.id
│   └── event.py                   # FK: support_id → collaborators.id (nullable)
│
├── db/
│   ├── __init__.py
│   └── session.py                 # Engine, SessionLocal, get_session()
│
├── services/                      # Business logic — all DB writes happen here
│   ├── __init__.py
│   ├── auth_service.py            # Login, token creation, password change
│   ├── collaborator_service.py
│   ├── client_service.py
│   ├── contract_service.py
│   └── event_service.py
│
├── cli/
│   ├── __init__.py
│   ├── app.py                     # Typer app — powers test suite and logout command
│   └── commands/
│       ├── auth.py                # Login / logout / password change
│       ├── collaborators.py       # Management-only CRUD
│       ├── clients.py
│       ├── contracts.py
│       └── events.py
│
├── views/                         # Rich output only — no business logic
│   ├── __init__.py
│   ├── menus.py                   # Role-scoped menu loop
│   ├── tables.py                  # Rich table renderers
│   ├── messages.py                # All user-facing strings centralised
│   ├── collaborators.py
│   ├── clients.py
│   ├── contracts.py
│   └── events.py
│
├── permissions/
│   ├── __init__.py
│   ├── roles.py                   # Role constants
│   └── decorators.py              # @require_role(*roles) — raises PermissionDeniedError
│
├── exceptions.py                  # All custom domain exceptions
├── config.py                      # Loads .env, exposes Settings object
│
├── migrations/
│   ├── env.py                     # Alembic env — reads DATABASE_URL from config
│   ├── script.py.mako
│   └── versions/                  # Auto-generated migration scripts (committed)
│
├── tests/
│   ├── conftest.py                # Shared fixtures (session, seeded objects)
│   ├── unit/
│   │   ├── models/
│   │   │   ├── test_client.py
│   │   │   ├── test_collaborator.py
│   │   │   ├── test_contract.py
│   │   │   ├── test_event.py
│   │   │   └── test_role.py
│   │   └── test_decorators.py
│   ├── integration/               # Runs against epic_events_test; tx rollback per test
│   └── functional/                # Full CLI stack via Typer CliRunner
│
├── .github/
│   ├── workflows/ci.yml           # CI: lint → test → coverage on every PR
│   └── ISSUE_TEMPLATE/
│       ├── epic.yml
│       ├── user_story.yml
│       └── bug_report.yml
│
├── .env.example                   # Variable names only — safe to commit
├── .gitignore
├── alembic.ini                    # Alembic config (script_location, sqlalchemy.url)
├── pyproject.toml                 # black + isort + coverage config
├── setup.cfg                      # flake8 config
├── pytest.ini                     # pytest config (testpaths, markers)
├── Makefile                       # format / lint / check / test / coverage shortcuts
├── requirements.txt               # Production dependencies
├── requirements-dev.txt           # Dev dependencies (pytest, black, flake8, etc.)
└── README.md
```

---

## Sentry Setup

Epic Events CRM uses [Sentry](https://sentry.io) for real-time error tracking.
All unhandled exceptions and key security events (permission violations, failed
logins) are captured automatically with full stack traces.

### 1. Create a Sentry account and project

1. Go to [sentry.io](https://sentry.io) and sign up (free tier is sufficient)
2. Create a new project → select **Python**
3. Copy the DSN: **Settings → Projects → your project → Client Keys (DSN)**

### 2. Add the DSN to your environment

```env
SENTRY_DSN=https://your-key@o0000000.ingest.sentry.io/0000000
```

Sentry is initialised at app startup inside `config.py` (or `main.py`):

```python
import sentry_sdk

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    traces_sample_rate=1.0,
    environment="production",
)
```

> If `SENTRY_DSN` is empty or not set, the SDK is a no-op — the app runs
> normally without any Sentry calls.

### 3. What is logged

| Event | Sentry level |
|---|---|
| Unhandled exceptions | `error` |
| `PermissionDeniedError` — unauthorised action attempt | `warning` |
| Failed login attempt | `warning` |
| Critical DB operation failure | `error` |

### 4. Viewing events

Log in to [sentry.io](https://sentry.io) → select your project:

- **Issues** — every captured exception with stack trace, user context, and
  breadcrumb trail
- **Performance** → Transactions — traces for each CLI session
- **Dashboards** — create a custom dashboard (see below)

### 5. Creating a Sentry dashboard for the demo

1. In your Sentry project, go to **Dashboards → Create Dashboard**
2. Name it `Epic Events — Demo`
3. Add the following widgets:

| Widget | Type | Query |
|---|---|---|
| Total errors (all time) | Big Number | `event.type:error` |
| Errors over time | Line chart | `event.type:error` |
| Permission violations | Big Number | `PermissionDeniedError` |
| Failed logins | Big Number | `failed login` |
| Latest issues | Issue list | (default) |

4. Click **Save** — this dashboard will be the first thing you open during
   the soutenance to show Sentry is active and capturing events.

> **Tip for the demo:** Before the soutenance, deliberately trigger a
> `PermissionDeniedError` by attempting a forbidden action (e.g. a Support
> user trying to create a collaborator). This ensures at least one real event
> appears in the dashboard.

---

## Security

### SQL Injection — SQLAlchemy ORM

All database interactions use **SQLAlchemy 2.x ORM** with parameterised
queries. Raw SQL strings are never constructed from user input. SQLAlchemy's
`select()`, `where()`, and `update()` constructs bind all parameters
automatically, making SQL injection structurally impossible at the data layer.

```python
# ✅ Safe — SQLAlchemy binds `email` as a parameter, never string-interpolated
stmt = select(Client).where(Client.email == email)
session.scalars(stmt)
```

### Password Storage — bcrypt

Passwords are **never stored in plain text**. On creation or update, passwords
are hashed using `bcrypt` with a cost factor of 12:

```python
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
```

Verification uses `bcrypt.checkpw()` — the plain-text password is never
logged, stored, or exposed after the hash is produced. The cost factor makes
offline dictionary attacks computationally expensive.

### Forced Password Change on First Login

Newly created collaborators have `must_change_password = True`. On first
login, the user is **forced to set a new password** before the menu is shown.
This ensures that temporary credentials assigned by a manager cannot be used
in production sessions and that the manager never knows a colleague's working
password.

### JWT Session Tokens

After successful authentication, the app issues a signed **JSON Web Token**
containing the collaborator's ID and role. The token is:

- Signed with `SECRET_KEY` using the HS256 algorithm
- Set to expire after **8 hours** (configurable via `JWT_EXPIRY_HOURS`)
- Stored at `~/.epic_events/session` outside the project directory, with
  permissions set to `chmod 600` (owner read/write only)

No session state is held server-side. Each protected action re-verifies the
token signature and expiry before executing.

### Role-Based Access Control — `@require_role`

Every service function that performs a write or sensitive read is decorated
with `@require_role(...)`. The check runs **before** any database interaction:

```python
@require_role("Management", "Commercial")
def update_client(session, token, client_id, **kwargs): ...
```

Attempting to call a protected function with an insufficient role raises a
`PermissionDeniedError` immediately. These attempts are captured by Sentry
as `warning`-level events.

### Brute Force Mitigation

Failed login attempts are captured by Sentry as warnings with the attempted
email and a timestamp. Sentry alert rules can be configured to notify (email
or Slack) when the same source generates more than N failed logins within a
time window. At the infrastructure level, the database user holds only
`SELECT / INSERT / UPDATE / DELETE` — no `CREATEDB`, no `SUPERUSER`.

### Secrets Management

All credentials (database URL, JWT secret key, Sentry DSN) are stored in
**environment variables** loaded via `python-dotenv`. The `.env` file is
excluded from version control via `.gitignore`. Only `.env.example` — with
empty values — is committed to the repository.

### PII Scrubbing in Sentry

Sentry is initialised with a `before_send` hook that strips sensitive fields
(passwords, tokens) from event payloads before they leave the process:

```python
def before_send(event, hint):
    if "request" in event:
        event["request"].pop("data", None)
    return event

sentry_sdk.init(dsn=..., before_send=before_send)
```

---

## Contributing

1. Branch from `develop`: `feature/US-XX-short-description`
2. Write tests first (TDD) — unit tests for logic, integration for services
3. Ensure `pytest --cov-fail-under=80` passes
4. Run `make check` before pushing
5. Open a pull request targeting `develop`, referencing the GitHub Issue:
   `Closes #XX`
6. CI runs automatically — the PR cannot be merged if linting or tests fail

---

*Epic Events CRM — OpenClassrooms Python back-end school project*