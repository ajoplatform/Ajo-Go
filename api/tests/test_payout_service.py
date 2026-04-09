import pytest
from api.app.services.payout_service import (
    get_next_recipient,
    calculate_payout_amount,
    advance_cycle,
)


class TestGetNextRecipient:
    def test_no_payouts_returns_first_member(self):
        members = [{"id": 1, "rotation_order": 1}, {"id": 2, "rotation_order": 2}]
        payouts = []
        result = get_next_recipient(members, payouts, current_cycle=1)
        assert result["id"] == 1

    def test_member_one_paid_returns_member_two(self):
        members = [{"id": 1, "rotation_order": 1}, {"id": 2, "rotation_order": 2}]
        payouts = [{"member_id": 1, "cycle_number": 1}]
        result = get_next_recipient(members, payouts, current_cycle=1)
        assert result["id"] == 2

    def test_last_member_paid_returns_none(self):
        members = [{"id": 1, "rotation_order": 1}, {"id": 2, "rotation_order": 2}]
        payouts = [
            {"member_id": 1, "cycle_number": 1},
            {"member_id": 2, "cycle_number": 1},
        ]
        result = get_next_recipient(members, payouts, current_cycle=1)
        assert result is None

    def test_skipped_member(self):
        members = [
            {"id": 1, "rotation_order": 1},
            {"id": 2, "rotation_order": 2},
            {"id": 3, "rotation_order": 3},
        ]
        payouts = [
            {"member_id": 1, "cycle_number": 1},
            {"member_id": 3, "cycle_number": 1},
        ]
        result = get_next_recipient(members, payouts)
        assert result["id"] == 2

    def test_no_members_returns_none(self):
        result = get_next_recipient([], [])
        assert result is None


class TestCalculatePayoutAmount:
    def test_five_members_five_thousand_each(self):
        contributions = [
            {"member_id": 1, "amount": 5000},
            {"member_id": 2, "amount": 5000},
            {"member_id": 3, "amount": 5000},
            {"member_id": 4, "amount": 5000},
            {"member_id": 5, "amount": 5000},
        ]
        result = calculate_payout_amount(contributions)
        assert result == 25000

    def test_member_with_zero_contribution(self):
        contributions = [{"member_id": 1, "amount": 0}]
        result = calculate_payout_amount(contributions)
        assert result == 0

    def test_no_contributions(self):
        result = calculate_payout_amount([])
        assert result == 0


class TestAdvanceCycle:
    def test_last_member_pays_advances_cycle(self, db_session):
        group = create_group(current_cycle_number=1)
        members = [create_member(group, i) for i in range(1, 4)]
        for m in members:
            create_contribution(m)
        result = advance_cycle(db_session, group.id)
        assert result.new_cycle_number == 2
