import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch


@pytest.fixture
def client(db_session):
    from api.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers():
    from unittest.mock import MagicMock

    with patch("api.app.core.auth.get_supabase") as mock_get_supabase:
        mock_client = MagicMock()
        mock_client.auth.get_user.return_value = MagicMock(
            user=MagicMock(id="test-admin-id", email="admin@test.com")
        )
        mock_get_supabase.return_value = mock_client
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def cron_secret(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-cron-secret")
    return "test-cron-secret"


@pytest.fixture(scope="function")
def db_session():
    from api.app.db.database import engine
    from api.app.db.models import Base

    # Create all tables
    Base.metadata.create_all(bind=engine)

    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=engine)
    session = Session()

    # Yield for test use
    yield session

    # Cleanup after test
    session.close()
    # Drop all tables for clean state next test
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def two_admins(client, db_session, auth_headers):
    """Fixture that creates two admins with separate groups for RLS testing."""
    from api.app.db.models import Admin, Group

    # First admin
    admin1 = Admin(email="admin1@test.com")
    db_session.add(admin1)
    db_session.commit()

    group1 = Group(admin_id=admin1.id, name="Admin 1 Group", contribution_amount=5000)
    db_session.add(group1)
    db_session.commit()

    # Second admin
    admin2 = Admin(email="admin2@test.com")
    db_session.add(admin2)
    db_session.commit()

    group2 = Group(admin_id=admin2.id, name="Admin 2 Group", contribution_amount=3000)
    db_session.add(group2)
    db_session.commit()

    # Return headers and the group id belonging to admin2
    return {
        "admin_a_headers": auth_headers,
        "admin_b_group_id": group2.id,
    }


@pytest.fixture
def group(db_session):
    """Create a test group in the database."""
    from api.app.db.models import Admin, Group

    admin = Admin(email="testgroup@admin.com")
    db_session.add(admin)
    db_session.commit()

    group = Group(admin_id=admin.id, name="Test Group", contribution_amount=5000)
    db_session.add(group)
    db_session.commit()
    return group


@pytest.fixture
def member():
    return {
        "id": 1,
        "group_id": 1,
        "name": "Chidi",
        "phone": "+2348012345678",
        "rotation_order": 1,
    }


@pytest.fixture
def member_invalid_phone():
    return {
        "id": 2,
        "group_id": 1,
        "name": "Bad Phone",
        "phone": "invalid",
        "rotation_order": 2,
    }


@pytest.fixture
def reminder_rule():
    return {
        "id": 1,
        "group_id": 1,
        "days_before_payout": 1,
        "message": "Reminder",
        "is_active": True,
    }


@pytest.fixture
def reminder_rule_inactive():
    return {
        "id": 2,
        "group_id": 1,
        "days_before_payout": 1,
        "message": "Reminder",
        "is_active": False,
    }


@pytest.fixture
def reminder_rule_due():
    return {
        "id": 3,
        "group_id": 1,
        "days_before_payout": 0,
        "message": "Due today!",
        "is_active": True,
    }


@pytest.fixture
def reminder_state():
    return {
        "group_id": 1,
        "current_cycle_number": 1,
        "last_reminder_sent_at": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def reminder_rule_due(db_session, group):
    from api.db.models import ReminderRule

    rule = ReminderRule(
        group_id=group["id"],
        days_before_payout=0,
        message="Due today!",
        is_active=True,
    )
    db_session.add(rule)
    db_session.commit()
    return rule


def create_group(**kwargs):
    return {
        "id": 1,
        "name": "Test Group",
        "contribution_amount": 5000,
        "current_cycle_number": 1,
        **kwargs,
    }


def create_member(group, rotation_order):
    return {
        "id": rotation_order,
        "group_id": group["id"],
        "rotation_order": rotation_order,
    }


def create_contribution(member):
    return {"id": 1, "member_id": member["id"], "amount": 5000, "date": date.today()}
