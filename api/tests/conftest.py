import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock, patch


@pytest.fixture
def client():
    from api.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers():
    with patch("api.auth.supabase_client") as mock:
        mock.auth.get_user.return_value = MagicMock(
            user=MagicMock(id="test-admin-id", email="admin@test.com")
        )
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def cron_secret(monkeypatch):
    monkeypatch.setenv("CRON_SECRET", "test-cron-secret")
    return "test-cron-secret"


@pytest.fixture
def db_session():
    pass


@pytest.fixture
def group():
    return {
        "id": 1,
        "name": "Test Group",
        "contribution_amount": 5000,
        "current_cycle_number": 1,
    }


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
