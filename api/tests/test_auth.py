import pytest
from unittest.mock import patch, MagicMock


class TestMagicLinkLogin:
    def test_magic_link_sent_on_signup(self, client):
        with patch("api.app.core.auth.supabase_client") as mock:
            mock.auth.sign_in_with_otp = MagicMock()
            response = client.post(
                "/api/auth/magic-link",
                json={"email": "reghie@example.com"},
            )
            assert response.status_code == 200
            mock.auth.sign_in_with_otp.assert_called_once()


class TestJWTValidation:
    def test_protected_endpoint_without_token_returns_401(self, client):
        response = client.get("/api/groups")
        assert response.status_code == 401

    def test_valid_jwt_allows_access(self, client, auth_headers):
        response = client.get("/api/groups", headers=auth_headers)
        assert response.status_code == 200


class TestRowLevelSecurity:
    def test_admin_cannot_access_other_admin_groups(self, client, two_admins):
        admin_a_headers = two_admins["admin_a_headers"]
        admin_b_group_id = two_admins["admin_b_group_id"]
        response = client.get(
            f"/api/groups/{admin_b_group_id}", headers=admin_a_headers
        )
        assert response.status_code == 403
