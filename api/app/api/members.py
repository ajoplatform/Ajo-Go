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

from apps.models.savings_groups import SavingsGroup, GroupMember

router = APIRouter(prefix="/api/groups/{group_id}/members", tags=["members"])

User = get_user_model()


def get_current_user(request):
    """Get current user from request - simplified for now."""
    return request


def get_group_or_404(group_id: int, user) -> SavingsGroup:
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")
    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")
    return group


class MemberCreate(BaseModel):
    # For now, use alias (name) directly since we may not have User objects for each member
    alias: str
    phone: str
    rotation_order: int
    # Optional: link to existing User
    user_id: Optional[int] = None


class MemberUpdate(BaseModel):
    alias: Optional[str] = None
    phone: Optional[str] = None
    rotation_order: Optional[int] = None


class MemberResponse(BaseModel):
    id: int
    group_id: int
    alias: str
    phone: str
    rotation_order: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.post("", response_model=MemberResponse, status_code=201)
def create_member(
    group_id: int,
    member: MemberCreate,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)

    # Get user object if user_id provided, otherwise None
    member_user = None
    if member.user_id:
        try:
            member_user = User.objects.get(id=member.user_id)
        except User.DoesNotExist:
            pass

    db_member = GroupMember.objects.create(
        group=group,
        member=member_user,
        alias=member.alias,
        phone=member.phone,
        rotation_order=member.rotation_order,
    )
    return db_member


@router.get("", response_model=List[MemberResponse])
def list_members(
    group_id: int,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)
    members = GroupMember.objects.filter(group=group).order_by('rotation_order')
    return members


@router.get("/{member_id}", response_model=MemberResponse)
def get_member(
    group_id: int,
    member_id: int,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)
    try:
        member = GroupMember.objects.get(id=member_id, group=group)
    except GroupMember.DoesNotExist:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.put("/{member_id}", response_model=MemberResponse)
def update_member(
    group_id: int,
    member_id: int,
    member_update: MemberUpdate,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)
    try:
        member = GroupMember.objects.get(id=member_id, group=group)
    except GroupMember.DoesNotExist:
        raise HTTPException(status_code=404, detail="Member not found")

    if member_update.alias is not None:
        member.alias = member_update.alias
    if member_update.phone is not None:
        member.phone = member_update.phone
    if member_update.rotation_order is not None:
        member.rotation_order = member_update.rotation_order

    member.save()
    return member


@router.delete("/{member_id}", status_code=204)
def delete_member(
    group_id: int,
    member_id: int,
    user=Depends(get_current_user),
):
    group = get_group_or_404(group_id, user)
    try:
        member = GroupMember.objects.get(id=member_id, group=group)
    except GroupMember.DoesNotExist:
        raise HTTPException(status_code=404, detail="Member not found")

    member.delete()
    return None