from typing import Optional
from dataclasses import dataclass


@dataclass
class PayoutResult:
    member_id: int
    amount: int
    cycle_number: int


def get_next_recipient(
    members: list[dict], payouts: list[dict], current_cycle: int
) -> Optional[dict]:
    if not members:
        return None

    paid_member_ids = {
        p["member_id"] for p in payouts if p.get("cycle_number") == current_cycle
    }

    sorted_members = sorted(members, key=lambda m: m.get("rotation_order", 0))

    for member in sorted_members:
        if member["id"] not in paid_member_ids:
            return member

    return None


def calculate_payout_amount(contribution_amount: int, member_count: int) -> int:
    if member_count <= 0 or contribution_amount <= 0:
        return 0
    return contribution_amount * member_count


def advance_cycle(
    current_cycle: int, member_count: int, paid_count: int
) -> Optional[int]:
    if paid_count >= member_count and member_count > 0:
        return current_cycle + 1
    return None


def is_cycle_complete(
    members: list[dict], payouts: list[dict], current_cycle: int
) -> bool:
    if not members:
        return False

    paid_member_ids = {
        p["member_id"] for p in payouts if p.get("cycle_number") == current_cycle
    }

    return len(paid_member_ids) >= len(members)
