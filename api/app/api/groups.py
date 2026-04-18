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

from apps.models.savings_groups import SavingsGroup, GroupMember, Contribution, Payout, ReminderRule, ReminderState

router = APIRouter(prefix="/api/groups", tags=["groups"])

User = get_user_model()


def get_current_user(request):
    """Get current user from request - simplified for now."""
    # TODO: integrate with django-allauth session
    return request


class GroupCreate(BaseModel):
    name: str
    contribution_amount: int
    payout_schedule: str = "monthly"


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    contribution_amount: Optional[int] = None
    payout_schedule: Optional[str] = None


class GroupResponse(BaseModel):
    id: int
    name: str
    contribution_amount: int
    payout_schedule: str
    current_cycle_number: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(
    group: GroupCreate,
    user=Depends(get_current_user),
):
    db_group = SavingsGroup.objects.create(
        created_by=user,
        name=group.name,
        contribution_amount=group.contribution_amount,
        payout_schedule=group.payout_schedule,
    )

    return db_group


@router.get("", response_model=List[GroupResponse])
def list_groups(user=Depends(get_current_user)):
    groups = SavingsGroup.objects.filter(created_by=user).all()
    return groups


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    user=Depends(get_current_user),
):
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")

    return group


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    group_update: GroupUpdate,
    user=Depends(get_current_user),
):
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")

    if group_update.name is not None:
        group.name = group_update.name
    if group_update.contribution_amount is not None:
        group.contribution_amount = group_update.contribution_amount
    if group_update.payout_schedule is not None:
        group.payout_schedule = group_update.payout_schedule

    group.save()
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    user=Depends(get_current_user),
):
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")

    group.delete()
    return None