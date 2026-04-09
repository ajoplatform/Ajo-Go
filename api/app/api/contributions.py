from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from api.app.db.database import get_db
from api.app.db.models import Group, Member, Contribution, Admin
from api.app.core.auth import get_current_admin


router = APIRouter(
    prefix="/api/groups/{group_id}/contributions", tags=["contributions"]
)


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


def get_group_or_404(group_id: int, db: Session, admin: dict) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if group.admin_id != admin_obj.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return group


@router.post("", response_model=ContributionResponse, status_code=201)
def create_contribution(
    group_id: int,
    contribution: ContributionCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)

    member = (
        db.query(Member)
        .filter(Member.id == contribution.member_id, Member.group_id == group_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if contribution.amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")

    db_contribution = Contribution(
        group_id=group_id,
        member_id=contribution.member_id,
        amount=contribution.amount,
        date=contribution.date,
        source=contribution.source,
    )
    db.add(db_contribution)
    db.commit()
    db.refresh(db_contribution)
    return db_contribution


@router.get("", response_model=List[ContributionResponse])
def list_contributions(
    group_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)
    contributions = (
        db.query(Contribution).filter(Contribution.group_id == group_id).all()
    )
    return contributions


@router.get("/{contribution_id}", response_model=ContributionResponse)
def get_contribution(
    group_id: int,
    contribution_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)
    contribution = (
        db.query(Contribution)
        .filter(Contribution.id == contribution_id, Contribution.group_id == group_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")
    return contribution


@router.delete("/{contribution_id}", status_code=204)
def delete_contribution(
    group_id: int,
    contribution_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)
    contribution = (
        db.query(Contribution)
        .filter(Contribution.id == contribution_id, Contribution.group_id == group_id)
        .first()
    )
    if not contribution:
        raise HTTPException(status_code=404, detail="Contribution not found")

    db.delete(contribution)
    db.commit()
    return None
