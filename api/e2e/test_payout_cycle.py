import pytest
from playwright.sync_api import Page


class TestPayoutCycle:
    def test_full_payout_cycle_advances_correctly(
        self, page: Page, admin_login, create_group
    ):
        group = create_group(name="Payout Test Group", contribution_amount=1000)
        members = add_members_to_group(group, count=3)

        for member in members:
            record_contribution(member=member, amount=1000)

        record_payout(member=members[0])

        updated_group = refresh_group(group.id)
        assert updated_group.current_cycle_number == 2

        next_recipient = get_next_recipient_for_group(group.id)
        assert next_recipient.id == members[1].id
