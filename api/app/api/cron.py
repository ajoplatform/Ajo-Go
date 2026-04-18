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

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timedelta

from apps.models.savings_groups import SavingsGroup, GroupMember, ReminderRule, ReminderState

router = APIRouter(prefix="/api/cron", tags=["cron"])


def get_current_user(request):
    return request


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
):
    expected_secret = os.getenv("CRON_SECRET")
    if expected_secret and cron_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")

    groups = SavingsGroup.objects.all()
    reminders_sent = 0

    for group in groups:
        reminder_rules = ReminderRule.objects.filter(
            group=group, is_active=True
        ).all()

        for rule in reminder_rules:
            reminder_state = ReminderState.objects.filter(group=group).first()

            if reminder_state and reminder_state.last_reminder_sent_at:
                last_sent = reminder_state.last_reminder_sent_at
                if (datetime.utcnow() - last_sent) < timedelta(hours=23):
                    continue

            members = GroupMember.objects.filter(group=group).all()
            for member in members:
                pass

            if not reminder_state:
                reminder_state = ReminderState.objects.create(
                    group=group, current_cycle_number=group.current_cycle_number
                )

            reminder_state.last_reminder_sent_at = datetime.utcnow()
            reminder_state.save()
            reminders_sent += 1

    return CronResponse(reminders_sent=reminders_sent, groups_checked=len(groups))


@router.post(
    "/groups/{group_id}/reminder-rules",
    response_model=ReminderRuleResponse,
    status_code=201,
)
def create_reminder_rule(
    group_id: int,
    rule: ReminderRuleCreate,
    user=Depends(get_current_user),
):
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")

    db_rule = ReminderRule.objects.create(
        group=group,
        days_before_payout=rule.days_before_payout,
        message=rule.message,
        is_active=rule.is_active,
    )
    return db_rule


@router.get(
    "/groups/{group_id}/reminder-rules", response_model=List[ReminderRuleResponse]
)
def list_reminder_rules(
    group_id: int,
    user=Depends(get_current_user),
):
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")

    rules = ReminderRule.objects.filter(group=group).all()
    return rules