import pytest
from datetime import date, timedelta
from pydantic import ValidationError


class TestContributionValidation:
    def test_zero_amount_raises_error(self):
        with pytest.raises(ValidationError):
            from api.schemas import ContributionCreate

            ContributionCreate(amount=0, member_id=1, date=date.today())

    def test_negative_amount_raises_error(self):
        with pytest.raises(ValidationError):
            from api.schemas import ContributionCreate

            ContributionCreate(amount=-1000, member_id=1, date=date.today())

    def test_future_date_raises_error(self):
        with pytest.raises(ValidationError):
            from api.schemas import ContributionCreate

            ContributionCreate(
                amount=5000, member_id=1, date=date.today() + timedelta(days=1)
            )

    def test_member_not_in_group_raises_403(self, client, auth_headers, group):
        response = client.post(
            "/api/contributions",
            json={"amount": 5000, "member_id": 9999, "date": str(date.today())},
            headers=auth_headers,
        )
        assert response.status_code == 403


class TestDuplicateDetection:
    def test_same_member_date_amount_rejected(
        self, client, auth_headers, group, member
    ):
        client.post(
            "/api/contributions",
            json={"amount": 5000, "member_id": member.id, "date": str(date.today())},
            headers=auth_headers,
        )
        response = client.post(
            "/api/contributions",
            json={"amount": 5000, "member_id": member.id, "date": str(date.today())},
            headers=auth_headers,
        )
        assert response.status_code in (409, 400)

    def test_same_member_different_amount_allowed(
        self, client, auth_headers, group, member
    ):
        client.post(
            "/api/contributions",
            json={"amount": 5000, "member_id": member.id, "date": str(date.today())},
            headers=auth_headers,
        )
        response = client.post(
            "/api/contributions",
            json={"amount": 6000, "member_id": member.id, "date": str(date.today())},
            headers=auth_headers,
        )
        assert response.status_code == 201

    def test_same_amount_different_date_allowed(
        self, client, auth_headers, group, member
    ):
        today = date.today()
        client.post(
            "/api/contributions",
            json={"amount": 5000, "member_id": member.id, "date": str(today)},
            headers=auth_headers,
        )
        response = client.post(
            "/api/contributions",
            json={
                "amount": 5000,
                "member_id": member.id,
                "date": str(today + timedelta(days=1)),
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
