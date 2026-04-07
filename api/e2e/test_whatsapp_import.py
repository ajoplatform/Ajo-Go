import pytest
from playwright.sync_api import Page, expect
from datetime import date


class TestWhatsAppImport:
    def test_full_import_flow(self, page: Page, admin_login, create_group):
        group = create_group(name="Import Test Group")
        page.goto(f"/groups/{group.id}/import")

        file_input = page.locator('input[type="file"]')
        file_input.set_input_files("tests/fixtures/sample_whatsapp_export.txt")

        page.wait_for_selector('[data-testid="parsed-results"]')
        results = page.locator('[data-testid="parsed-contribution"]')
        initial_count = results.count()
        assert initial_count >= 1

        page.locator('[data-testid="delete-contribution"]').first.click()
        page.locator('[data-testid="edit-amount"]').first.fill("4000")

        page.locator('[data-testid="confirm-import"]').click()
        page.wait_for_selector('[data-testid="import-success"]')

        contributions = get_contributions_for_group(group.id)
        assert len(contributions) == initial_count - 1
