from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from api.app.db.database import get_db
from api.app.db.models import Group, Member, Admin
from api.app.core.auth import get_current_admin


router = APIRouter(prefix="/api/groups/{group_id}/members", tags=["members"])


class MemberCreate(BaseModel):
    name: str
    phone: str
    rotation_order: int


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    rotation_order: Optional[int] = None


class MemberResponse(BaseModel):
    id: int
    group_id: int
    name: str
    phone: str
    rotation_order: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


def get_group_or_404(group_id: int, db: Session, admin: dict) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if group.admin_id != admin_obj.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return group


@router.post("", response_model=MemberResponse, status_code=201)
def create_member(
    group_id: int,
    member: MemberCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)

    db_member = Member(
        group_id=group_id,
        name=member.name,
        phone=member.phone,
        rotation_order=member.rotation_order,
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


@router.get("", response_model=List[MemberResponse])
def list_members(
    group_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)
    members = (
        db.query(Member)
        .filter(Member.group_id == group_id)
        .order_by(Member.rotation_order)
        .all()
    )
    return members


@router.get("/{member_id}", response_model=MemberResponse)
def get_member(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.group_id == group_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.put("/{member_id}", response_model=MemberResponse)
def update_member(
    group_id: int,
    member_id: int,
    member_update: MemberUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.group_id == group_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member_update.name is not None:
        member.name = member_update.name
    if member_update.phone is not None:
        member.phone = member_update.phone
    if member_update.rotation_order is not None:
        member.rotation_order = member_update.rotation_order

    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=204)
def delete_member(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)
    member = (
        db.query(Member)
        .filter(Member.id == member_id, Member.group_id == group_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()
    return None
