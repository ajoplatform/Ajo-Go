from django.contrib import admin

from apps.models import (
    SavingsGroup, GroupMember, Contribution, ReminderRule, ReminderState, Payout,
)


@admin.register(SavingsGroup)
class GroupAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "created_by",
        "contribution_amount",
        "contribution_schedule",
        "payout_schedule",
        "current_cycle_number",
        "member_count",
        "created_at",
    ]
    list_filter = ["payout_schedule", "created_at"]
    search_fields = ["name", "admin__email"]
    raw_id_fields = ["created_by"]
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


@admin.register(GroupMember)
class MemberAdmin(admin.ModelAdmin):
    list_display = ["group", "member", "rotation_order", "created_at"]
    list_filter = ["group"]
    search_fields = ["group__name", "member__phone", "group__name"]
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
