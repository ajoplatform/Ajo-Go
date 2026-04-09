from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from api.app.db.database import get_db
from api.app.db.models import Group, Admin
from api.app.core.auth import get_current_admin


router = APIRouter(prefix="/api/groups", tags=["groups"])


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
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if not admin_obj:
        admin_obj = Admin(email=admin["email"])
        db.add(admin_obj)
        db.commit()
        db.refresh(admin_obj)

    db_group = Group(
        admin_id=admin_obj.id,
        name=group.name,
        contribution_amount=group.contribution_amount,
        payout_schedule=group.payout_schedule,
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)

    return db_group


@router.get("", response_model=List[GroupResponse])
def list_groups(
    db: Session = Depends(get_db), admin: dict = Depends(get_current_admin)
):
    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if not admin_obj:
        return []

    groups = db.query(Group).filter(Group.admin_id == admin_obj.id).all()
    return groups


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if group.admin_id != admin_obj.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    return group


@router.put("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    group_update: GroupUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if group.admin_id != admin_obj.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if group_update.name is not None:
        group.name = group_update.name
    if group_update.contribution_amount is not None:
        group.contribution_amount = group_update.contribution_amount
    if group_update.payout_schedule is not None:
        group.payout_schedule = group_update.payout_schedule

    db.commit()
    db.refresh(group)
    return group


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if group.admin_id != admin_obj.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(group)
    db.commit()
    return None
