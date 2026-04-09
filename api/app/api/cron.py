from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import os

from api.app.db.database import get_db
from api.app.db.models import Group, Member, ReminderRule, ReminderState, Admin
from api.app.core.auth import get_current_admin


router = APIRouter(prefix="/api/cron", tags=["cron"])


class ReminderRuleCreate(BaseModel):
    days_before_payout: int = 1
    message: str = "Reminder: Payment is due soon"
    is_active: bool = True


class ReminderRuleResponse(BaseModel):
    id: int
    group_id: int
    days_before_payout: int
    message: str
    is_active: bool

    class Config:
        from_attributes = True


class CronResponse(BaseModel):
    reminders_sent: int
    groups_checked: int


@router.get("/send-reminders", response_model=CronResponse)
def send_reminders(
    cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    db: Session = Depends(get_db),
):
    expected_secret = os.getenv("CRON_SECRET")
    if expected_secret and cron_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    groups = db.query(Group).all()
    reminders_sent = 0

    for group in groups:
        reminder_rules = (
            db.query(ReminderRule)
            .filter(ReminderRule.group_id == group.id, ReminderRule.is_active == True)
            .all()
        )

        for rule in reminder_rules:
            reminder_state = (
                db.query(ReminderState)
                .filter(ReminderState.group_id == group.id)
                .first()
            )

            if reminder_state and reminder_state.last_reminder_sent_at:
                last_sent = reminder_state.last_reminder_sent_at
                if (datetime.utcnow() - last_sent) < timedelta(hours=23):
                    continue

            members = db.query(Member).filter(Member.group_id == group.id).all()
            for member in members:
                pass

            if not reminder_state:
                reminder_state = ReminderState(
                    group_id=group.id, current_cycle_number=group.current_cycle_number
                )
                db.add(reminder_state)

            reminder_state.last_reminder_sent_at = datetime.utcnow()
            reminders_sent += 1

    db.commit()
    return CronResponse(reminders_sent=reminders_sent, groups_checked=len(groups))


@router.post(
    "/groups/{group_id}/reminder-rules",
    response_model=ReminderRuleResponse,
    status_code=201,
)
def create_reminder_rule(
    group_id: int,
    rule: ReminderRuleCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if group.admin_id != admin_obj.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db_rule = ReminderRule(
        group_id=group_id,
        days_before_payout=rule.days_before_payout,
        message=rule.message,
        is_active=rule.is_active,
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.get(
    "/groups/{group_id}/reminder-rules", response_model=List[ReminderRuleResponse]
)
def list_reminder_rules(
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

    rules = db.query(ReminderRule).filter(ReminderRule.group_id == group_id).all()
    return rules
