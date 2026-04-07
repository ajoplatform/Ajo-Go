import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class TestReminderLogic:
    def test_active_rule_approaching_due_date_included(
        self, db_session, group, reminder_rule
    ):
        from api.services.reminder_service import get_pending_reminders

        reminders = get_pending_reminders(db_session)
        assert len(reminders) >= 1

    def test_already_sent_today_excluded(self, db_session, group, reminder_state):
        from api.services.reminder_service import get_pending_reminders

        reminders = get_pending_reminders(db_session)
        assert all(r.group_id != reminder_state.group_id for r in reminders)

    def test_inactive_rule_excluded(self, db_session, group, reminder_rule_inactive):
        from api.services.reminder_service import get_pending_reminders

        reminders = get_pending_reminders(db_session)
        assert all(r.group_id != group.id for r in reminders)

    def test_invalid_phone_skipped_gracefully(
        self, db_session, group, member_invalid_phone, reminder_rule
    ):
        from api.services.reminder_service import send_reminder

        result = send_reminder(db_session, group.id, member_invalid_phone.id)
        assert result.skipped is True


class TestCronEndpoint:
    def test_missing_cron_secret_returns_401(self, client):
        response = client.get("/api/cron/send-reminders")
        assert response.status_code == 401

    def test_invalid_cron_secret_returns_401(self, client):
        response = client.get(
            "/api/cron/send-reminders",
            headers={"Authorization": "Bearer wrong-secret"},
        )
        assert response.status_code == 401

    def test_valid_secret_no_reminders_returns_200(self, client, cron_secret):
        response = client.get(
            "/api/cron/send-reminders",
            headers={"Authorization": f"Bearer {cron_secret}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sent"] == 0

    def test_valid_secret_sends_due_reminders(
        self, client, cron_secret, db_session, group, member, reminder_rule_due
    ):
        with patch("api.whatsapp.twilio_client") as mock_twilio:
            mock_twilio.messages.create = MagicMock()
            response = client.get(
                "/api/cron/send-reminders",
                headers={"Authorization": f"Bearer {cron_secret}"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["sent"] >= 1
            mock_twilio.messages.create.assert_called()
