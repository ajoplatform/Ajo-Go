import os
import sys
from pathlib import Path

# Add project root to path (api/ -> project root)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "api"))

# Configure Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django
django.setup()

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from django.contrib.auth import get_user_model

from apps.models.savings_groups import SavingsGroup, GroupMember, Payout
from api.app.services.payout_service import (
    get_next_recipient,
    calculate_payout_amount,
    is_cycle_complete,
)

router = APIRouter(prefix="/api/groups/{group_id}/payouts", tags=["payouts"])

User = get_user_model()


def get_current_user(request):
    return request


def get_group_or_404(group_id: int, user) -> SavingsGroup:
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")
    return group


class PayoutCreate(BaseModel):
    member_id: int
    amount: int
    payout_date: datetime


class PayoutResponse(BaseModel):
    id: int
    group_id: int
    cycle_number: int
    member_id: int
    amount: int
    payout_date: datetime
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NextRecipientResponse(BaseModel):
    member_id: Optional[int]
    name: Optional[str]
    amount: int


class GroupResponse(BaseModel):
    id: int
    name: str
    contribution_amount: int
    payout_schedule: str
    current_cycle_number: int

    class Config:
        from_attributes = True


@router.post("", response_model=PayoutResponse, status_code=201)
def create_payout(
    group_id: int,
    payout: PayoutCreate,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)

    try:
        member = GroupMember.objects.get(id=payout.member_id, group_id=group_id)
    except GroupMember.DoesNotExist:
        raise HTTPException(status_code=404, detail="Member not found")

    db_payout = Payout.objects.create(
        group=group,
        cycle_number=group.current_cycle_number,
        member=member,
        amount=payout.amount,
        payout_date=payout.payout_date,
    )

    members = GroupMember.objects.filter(group=group).all()

    all_payouts = Payout.objects.filter(
        group=group,
        cycle_number=group.current_cycle_number,
    ).all()

    payout_dicts = [
        {"member_id": p.member_id, "cycle_number": p.cycle_number}
        for p in all_payouts
    ] + [{"member_id": payout.member_id, "cycle_number": group.current_cycle_number}]

    if is_cycle_complete(
        [{"id": m.id, "rotation_order": m.rotation_order} for m in members],
        payout_dicts,
        group.current_cycle_number,
    ):
        group.current_cycle_number += 1
        group.save()

    return db_payout


@router.get("", response_model=List[PayoutResponse])
def list_payouts(
    group_id: int,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)
    payouts = Payout.objects.filter(group=group).order_by('-cycle_number')
    return payouts


@router.get("/next", response_model=NextRecipientResponse)
def get_next_payout_recipient(
    group_id: int,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)

    members = GroupMember.objects.filter(group=group).order_by('rotation_order')
    payouts = Payout.objects.filter(
        group=group,
        cycle_number=group.current_cycle_number,
    ).all()

    member_dicts = [{"id": m.id, "rotation_order": m.rotation_order} for m in members]
    payout_dicts = [
        {"member_id": p.member_id, "cycle_number": p.cycle_number} for p in payouts
    ]

    next_recipient = get_next_recipient(
        member_dicts, payout_dicts, group.current_cycle_number
    )

    if not next_recipient:
        return NextRecipientResponse(member_id=None, name=None, amount=0)

    member = GroupMember.objects.filter(id=next_recipient["id"]).first()
    amount = calculate_payout_amount(group.contribution_amount, len(members))

    return NextRecipientResponse(
        member_id=next_recipient["id"],
        name=member.alias if member else None,
        amount=amount,
    )


@router.post("/advance-cycle", response_model=GroupResponse)
def advance_cycle(
    group_id: int,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)
    group.current_cycle_number += 1
    group.save()
    return group