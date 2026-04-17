# /// script
# dependencies = [
#     "nanodjango",
#     "dj-database-url",
# ]
# ///

"""
AjoGo - Single-file Django admin with nanodjango
Digital Savings & Thrift Platform for West African markets
"""

import os

import dj_database_url
import nanodjango
from django.contrib import admin
from django.db import models

db_url = dj_database_url.config(
    default=os.getenv("DATABASE_URL", "sqlite:///db.sqlite3"),
    conn_max_age=600,
    conn_health_checks=True,
)

app = nanodjango.Django(
    INSTALLED_APPS=[
        "django.contrib.admin",
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "django.contrib.messages",
        "django.contrib.sessions",
    ],
    DATABASES={
        "default": db_url,
    },
    SECRET_KEY=os.getenv("DJANGO_SECRET_KEY", "changemebeforeproduction"),
    ALLOWED_HOSTS=["*"],
)


# ============== MODELS ==============


@app.admin(
    list_display=["id", "email", "name", "created_at"],
    search_fields=["email", "name"],
    list_filter=["created_at"],
)
class Admin(models.Model):
    email = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "admins"
        verbose_name = " Admin"
        verbose_name_plural = " Admins"

    def __str__(self):
        return self.email


class Group(models.Model):
    """Thrift group with contribution and payout settings"""

    PAYOUT_SCHEDULES = [
        ("weekly", "Weekly"),
        ("biweekly", "Bi-weekly"),
        ("monthly", "Monthly"),
    ]

    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField(max_length=255)
    contribution_amount = models.IntegerField()
    payout_schedule = models.CharField(
        max_length=50, choices=PAYOUT_SCHEDULES, default="monthly"
    )
    current_cycle_number = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "groups"
        verbose_name = " Group"
        verbose_name_plural = " Groups"

    def __str__(self):
        return self.name

    @property
    def member_count(self):
        return self.members.count()

    @property
    def next_recipient(self):
        """Get next member to receive payout in rotation"""
        paid_ids = set(
            self.payouts.filter(cycle_number=self.current_cycle_number).values_list(
                "member_id", flat=True
            )
        )
        for member in self.members.order_by("rotation_order"):
            if member.id not in paid_ids:
                return member
        return None


class Member(models.Model):
    """Group member with rotation order for payouts"""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    rotation_order = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "members"
        ordering = ["rotation_order"]
        verbose_name = " Member"

    def __str__(self):
        return f"{self.name} (order: {self.rotation_order})"


class Contribution(models.Model):
    """Member contribution record"""

    SOURCES = [
        ("manual", "Manual Entry"),
        ("whatsapp_import", "WhatsApp Import"),
    ]

    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="contributions"
    )
    member = models.ForeignKey(
        Member, on_delete=models.CASCADE, related_name="contributions"
    )
    amount = models.IntegerField()
    date = models.DateTimeField()
    source = models.CharField(max_length=50, choices=SOURCES, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contributions"
        verbose_name = "Contribution"
        verbose_name_plural = "Contributions"

    def __str__(self):
        return f"{self.member.name}: {self.amount} on {self.date.date()}"


class ReminderRule(models.Model):
    """Reminder schedule for a group"""

    group = models.ForeignKey(
        Group, on_delete=models.CASCADE, related_name="reminder_rules"
    )
    days_before_payout = models.IntegerField(default=1)
    message = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reminder_rules"

    def __str__(self):
        return f"{self.group.name}: {self.days_before_payout} days before"


class ReminderState(models.Model):
    """Tracks reminder state per cycle for idempotency"""

    group = models.OneToOneField(
        Group, on_delete=models.CASCADE, related_name="reminder_state"
    )
    current_cycle_number = models.IntegerField()
    last_reminder_sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reminder_states"

    def __str__(self):
        return f"{self.group.name} - Cycle {self.current_cycle_number}"


class Payout(models.Model):
    """Payout record when member receives their payout"""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="payouts")
    cycle_number = models.IntegerField()
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.IntegerField()
    payout_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "payouts"

    def __str__(self):
        return f"{self.member.name}: {self.amount} in cycle {self.cycle_number}"


POST_TYPES = [
    ("post", "Post"),
    ("message", "Message"),
    ("comment", "Comment"),
]


class Post(models.Model):
    """Group post/message imported from WhatsApp"""

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name="posts")
    sender = models.CharField(max_length=100)
    content = models.TextField()
    post_type = models.CharField(max_length=10, choices=POST_TYPES, default="message")
    timestamp = models.DateTimeField()
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="comments"
    )
    raw_members = models.JSONField(default=list)
    raw_line = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posts"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.sender}: {self.post_type} on {self.timestamp.date()}"


# ============== ADMIN ==============
# @app.admin(Admin)
# class AdminAdmin(admin.ModelAdmin):
#     list_display = ["id", "email", "name", "created_at"]
#     search_fields = ["email", "name"]
#     list_filter = ["created_at"]


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "name",
        "admin",
        "contribution_amount",
        "payout_schedule",
        "current_cycle_number",
        "member_count",
        "created_at",
    ]
    list_filter = ["payout_schedule", "created_at"]
    search_fields = ["name", "admin__email"]
    raw_id_fields = ["admin"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Basic Info",
            {"fields": ("name", "admin", "contribution_amount", "payout_schedule")},
        ),
        ("Cycle", {"fields": ("current_cycle_number",)}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Member
class MemberAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "phone", "group", "rotation_order", "created_at"]
    list_filter = ["group"]
    search_fields = ["name", "phone", "group__name"]
    raw_id_fields = ["group"]
    ordering = ["group", "rotation_order"]


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = ["id", "member", "amount", "date", "source", "created_at"]
    list_filter = ["source", "date", "group"]
    search_fields = ["member__name", "group__name"]
    raw_id_fields = ["group", "member"]
    date_hierarchy = "date"
    ordering = ["-date"]


@admin.register(ReminderRule)
class ReminderRuleAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "group",
        "days_before_payout",
        "message_preview",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "days_before_payout"]
    search_fields = ["group__name"]
    raw_id_fields = ["group"]

    def message_preview(self, obj):
        return (
            (obj.message[:50] + "...")
            if obj.message and len(obj.message) > 50
            else obj.message
        )

    message_preview.short_description = "Message"


@admin.register(ReminderState)
class ReminderStateAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "group",
        "current_cycle_number",
        "last_reminder_sent_at",
        "updated_at",
    ]
    raw_id_fields = ["group"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "member",
        "amount",
        "cycle_number",
        "payout_date",
        "created_at",
    ]
    list_filter = ["cycle_number", "payout_date", "group"]
    search_fields = ["member__name", "group__name"]
    raw_id_fields = ["group", "member"]
    date_hierarchy = "payout_date"
    ordering = ["-payout_date"]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        "timestamp",
        "group",
        "sender",
        "post_type",
        "content_preview",
    ]
    list_filter = ["post_type", "timestamp", "group"]
    search_fields = ["sender", "content", "group__name"]
    raw_id_fields = ["group", "parent"]
    date_hierarchy = "timestamp"
    ordering = ["-timestamp"]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "group",
                    "sender",
                    "content",
                    "post_type",
                    "timestamp",
                    "parent",
                ]
            },
        ),
        (
            "Raw Data",
            {
                "fields": ["raw_members", "raw_line"],
                "classes": ["collapse"],
            },
        ),
    ]

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content

    content_preview.short_description = "Content"


# ============== MANAGEMENT COMMAND ==============

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "migrate":
            # Run migrations
            from django.core.management import call_command

            call_command("makemigrations", verbosity=2)
            call_command("migrate", verbosity=2)
            call_command("check", verbosity=2)
            print("✅ Migrations complete!")

        elif command == "changepassword":
            from django.core.management import call_command

            call_command("changepassword")

        elif command == "createsuperuser":
            from django.core.management import call_command

            call_command("createsuperuser")

        elif command == "check":
            from django.core.management import call_command

            call_command("check")

        elif command == "makemigrations":
            from django.core.management import call_command

            call_command("makemigrations")

        elif command == "runserver":
            import sys

            if len(sys.argv) > 2:
                app.run(sys.argv[2])
            else:
                app.run()

        else:
            print(f"Unknown command: {command}")
            print(
                "Available: check, makemigrations, migrate, createsuperuser, runserver"
            )
    else:
        # Default: run the app
        app.run()
