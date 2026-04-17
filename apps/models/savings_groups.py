from django.contrib.auth import get_user_model
from django.db import models


User = get_user_model()


class SavingsGroup(models.Model):
    """Thrift group with contribution and payout settings"""

    PAYOUT_SCHEDULES = [
        ("weekly", "Weekly"),
        ("biweekly", "Bi-weekly"),
        ("monthly", "Monthly"),
    ]
    name = models.CharField(max_length=255)
    contribution_amount = models.IntegerField()
    contribution_schedule = models.CharField( max_length=50, choices=PAYOUT_SCHEDULES, default="monthly", )
    payout_schedule = models.CharField( max_length=50, choices=PAYOUT_SCHEDULES, default="monthly", )
    current_cycle_number = models.IntegerField(default=1)
    created_by = models.ForeignKey( User, on_delete=models.DO_NOTHING, related_name="created_groups", )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "savings_groups"
        verbose_name = "   Savings Group"

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()


class GroupMember(models.Model):
    """Group member with rotation order for payouts"""

    group = models.ForeignKey( SavingsGroup, on_delete=models.DO_NOTHING, related_name="members", )
    member = models.ForeignKey( User, on_delete=models.DO_NOTHING, related_name="user", )
    rotation_order = models.IntegerField()
    alias = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "group_members"
        ordering = ["rotation_order"]
        verbose_name = "  Member"
        unique_together = (("group", "member", "rotation_order"),)

    def __str__(self):
        return f"{self.member.full_name} (order: {self.rotation_order})"



class Contribution(models.Model):
    """Member contribution record"""

    SOURCES = [("manual", "Manual Entry"), ("whatsapp_import", "WhatsApp Import")]
    group = models.ForeignKey(
        SavingsGroup, on_delete=models.CASCADE, related_name="contributions"
    )
    member = models.ForeignKey(
        GroupMember, on_delete=models.CASCADE, related_name="contributions"
    )
    amount = models.IntegerField()
    date = models.DateTimeField()
    source = models.CharField(max_length=50, choices=SOURCES, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contributions"
        verbose_name = " Contribution"

    def __str__(self):
        return f"{self.member.name}: {self.amount} on {self.date.date()}"


class ReminderRule(models.Model):
    """Reminder schedule for a group"""

    group = models.ForeignKey(
        SavingsGroup, on_delete=models.CASCADE, related_name="reminder_rules"
    )
    days_before_payout = models.IntegerField(default=1)
    message = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reminder_rules"
        verbose_name = " Reminder Rule"

    def __str__(self):
        return f"{self.group.name}: {self.days_before_payout} days before"


class ReminderState(models.Model):
    """Tracks reminder state per cycle for idempotency"""

    group = models.OneToOneField(
        SavingsGroup, on_delete=models.CASCADE, related_name="reminder_state"
    )
    current_cycle_number = models.IntegerField()
    last_reminder_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reminder_states"
        verbose_name = " Reminder State"

    def __str__(self):
        return f"{self.group.name} - Cycle {self.current_cycle_number}"


class Payout(models.Model):
    """Payout record when member receives their payout"""

    group = models.ForeignKey(
        SavingsGroup, on_delete=models.CASCADE, related_name="payouts"
    )
    cycle_number = models.IntegerField()
    member = models.ForeignKey(GroupMember, on_delete=models.CASCADE)
    amount = models.IntegerField()
    payout_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payouts"

    def __str__(self):
        return f"{self.member.name}: {self.amount} in cycle {self.cycle_number}"
