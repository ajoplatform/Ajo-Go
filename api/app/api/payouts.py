from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from api.app.db.database import get_db
from api.app.db.models import Group, Member, Payout, Admin
from api.app.core.auth import get_current_admin
from api.app.services.payout_service import (
    get_next_recipient,
    calculate_payout_amount,
    is_cycle_complete,
)


router = APIRouter(prefix="/api/groups/{group_id}/payouts", tags=["payouts"])


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


def get_group_or_404(group_id: int, db: Session, admin: dict) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if group.admin_id != admin_obj.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return group


@router.post("", response_model=PayoutResponse, status_code=201)
def create_payout(
    group_id: int,
    payout: PayoutCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)

    member = (
        db.query(Member)
        .filter(Member.id == payout.member_id, Member.group_id == group_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db_payout = Payout(
        group_id=group_id,
        cycle_number=group.current_cycle_number,
        member_id=payout.member_id,
        amount=payout.amount,
        payout_date=payout.payout_date,
    )
    db.add(db_payout)

    # Check if cycle is complete (including the new payout just added)
    members = db.query(Member).filter(Member.group_id == group_id).all()

    # Get all payouts including the one just added (before commit)
    all_payouts = (
        db.query(Payout)
        .filter(
            Payout.group_id == group_id,
            Payout.cycle_number == group.current_cycle_number,
        )
        .all()
    )

    # Include the newly created payout in the check
    payout_dicts = [
        {"member_id": p.member_id, "cycle_number": p.cycle_number} for p in all_payouts
    ] + [{"member_id": payout.member_id, "cycle_number": group.current_cycle_number}]

    if is_cycle_complete(
        [{"id": m.id, "rotation_order": m.rotation_order} for m in members],
        payout_dicts,
        group.current_cycle_number,
    ):
        group.current_cycle_number += 1

    db.commit()
    db.refresh(db_payout)
    return db_payout


@router.get("", response_model=List[PayoutResponse])
def list_payouts(
    group_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)
    payouts = (
        db.query(Payout)
        .filter(Payout.group_id == group_id)
        .order_by(Payout.cycle_number.desc())
        .all()
    )
    return payouts


@router.get("/next", response_model=NextRecipientResponse)
def get_next_payout_recipient(
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
    payouts = (
        db.query(Payout)
        .filter(
            Payout.group_id == group_id,
            Payout.cycle_number == group.current_cycle_number,
        )
        .all()
    )

    member_dicts = [{"id": m.id, "rotation_order": m.rotation_order} for m in members]
    payout_dicts = [
        {"member_id": p.member_id, "cycle_number": p.cycle_number} for p in payouts
    ]

    next_recipient = get_next_recipient(
        member_dicts, payout_dicts, group.current_cycle_number
    )

    if not next_recipient:
        return NextRecipientResponse(member_id=None, name=None, amount=0)

    member = db.query(Member).filter(Member.id == next_recipient["id"]).first()
    amount = calculate_payout_amount(group.contribution_amount, len(members))

    return NextRecipientResponse(
        member_id=next_recipient["id"],
        name=member.name if member else None,
        amount=amount,
    )


@router.post("/advance-cycle", response_model=GroupResponse)
def advance_cycle(
    group_id: int,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)
    group.current_cycle_number += 1
    db.commit()
    db.refresh(group)
    return group
