import pytest


class TestGroupCRUD:
    def test_create_group_returns_201(self, client, auth_headers):
        response = client.post(
            "/api/groups",
            json={
                "name": "Test Group",
                "contribution_amount": 5000,
                "payout_schedule": "monthly",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Group"
        assert data["current_cycle_number"] == 1

    def test_create_group_empty_name_returns_422(self, client, auth_headers):
        response = client.post(
            "/api/groups",
            json={
                "name": "",
                "contribution_amount": 5000,
                "payout_schedule": "monthly",
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_get_own_groups_returns_list(self, client, auth_headers, group):
        response = client.get("/api/groups", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(g["id"] == group.id for g in data)

    def test_get_other_admin_group_returns_403(self, client, two_admins):
        admin_a_headers = two_admins["admin_a_headers"]
        admin_b_group_id = two_admins["admin_b_group_id"]
        response = client.get(
            f"/api/groups/{admin_b_group_id}", headers=admin_a_headers
        )
        assert response.status_code == 403
