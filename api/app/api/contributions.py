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

from apps.models.savings_groups import SavingsGroup, GroupMember, Contribution

router = APIRouter(
    prefix="/api/groups/{group_id}/contributions", tags=["contributions"]
)

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


class ContributionCreate(BaseModel):
    member_id: int
    amount: int
    date: datetime
    source: str = "manual"


class ContributionResponse(BaseModel):
    id: int
    group_id: int
    member_id: int
    amount: int
    date: datetime
    source: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("", response_model=ContributionResponse, status_code=201)
def create_contribution(
    group_id: int,
    contribution: ContributionCreate,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)

    try:
        member = GroupMember.objects.get(id=contribution.member_id, group_id=group_id)
    except GroupMember.DoesNotExist:
        raise HTTPException(status_code=404, detail="Member not found")

    if contribution.amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")

    db_contribution = Contribution.objects.create(
        group=group,
        member=member,
        amount=contribution.amount,
        date=contribution.date,
        source=contribution.source,
    )
    return db_contribution


@router.get("", response_model=List[ContributionResponse])
def list_contributions(
    group_id: int,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)
    contributions = Contribution.objects.filter(group=group).all()
    return contributions


@router.get("/{contribution_id}", response_model=ContributionResponse)
def get_contribution(
    group_id: int,
    contribution_id: int,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)
    try:
        contribution = Contribution.objects.get(id=contribution_id, group=group)
    except Contribution.DoesNotExist:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return contribution


@router.delete("/{contribution_id}", status_code=204)
def delete_contribution(
    group_id: int,
    contribution_id: int,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)
    try:
        contribution = Contribution.objects.get(id=contribution_id, group=group)
    except Contribution.DoesNotExist:
        raise HTTPException(status_code=404, detail="Contribution not found")

    contribution.delete()
    return None