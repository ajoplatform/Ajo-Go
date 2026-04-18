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

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from django.db import transaction
from django.contrib.auth import get_user_model

from api.app.services.whatsapp_parser import (
    parse_file,
    WhatsAppParseResult,
    parse_whatsapp_posts,
    fuzzy_match_member,
)

# Import Django models
from apps.models.savings_groups import (
    SavingsGroup,
    GroupMember,
    Contribution,
    Payout,
    ReminderRule,
    ReminderState,
)
from apps.models.posts import Post as WhatsAppPost
from apps.models.users import MyUser

router = APIRouter(
    prefix="/api/groups/{group_id}/whatsapp-import", tags=["whatsapp-import"]
)

User = get_user_model()


def get_user_or_403(request):
    """Get current user from request - simplified for now."""
    # TODO: integrate with django-allauth session
    # For now, we'll use a simple approach
    return request


class ParsedContribution(BaseModel):
    sender: str
    amount: int
    confidence: float
    needs_review: bool
    raw_line: str


class ImportRequest(BaseModel):
    contributions: List[dict]
    source: str = "whatsapp_import"


class ImportResponse(BaseModel):
    imported: int
    skipped: int


def get_group_or_404(group_id: int, user) -> SavingsGroup:
    try:
        group = SavingsGroup.objects.get(id=group_id)
        if group.created_by != user:
            raise HTTPException(status_code=403, detail="Not authorized")
        return group
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")


@router.post("/parse", response_model=List[ParsedContribution])
def parse_whatsapp_export(
    group_id: int,
    file: UploadFile = File(...),
    user=Depends(get_user_or_403),
):
    content = file.file.read().decode("utf-8", errors="ignore")
    results = parse_file(content)

    return [
        ParsedContribution(
            sender=r.sender,
            amount=r.amount,
            confidence=r.confidence,
            needs_review=r.needs_review,
            raw_line=r.raw_line,
        )
        for r in results
    ]


@router.post("/import", response_model=ImportResponse)
def import_contributions(
    group_id: int,
    import_request: ImportRequest,
    user=Depends(get_user_or_403),
):
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")

    imported = 0
    skipped = 0

    for contrib in import_request.contributions:
        sender = contrib.get("sender")
        amount = contrib.get("amount")

        if not sender or not amount:
            skipped += 1
            continue

        # Find member by alias (name)
        member = GroupMember.objects.filter(
            group_id=group_id,
            alias__iexact=sender
        ).first()

        if not member:
            skipped += 1
            continue

        # Check for duplicates
        existing = Contribution.objects.filter(
            group_id=group_id,
            member_id=member.id,
            amount=amount,
        ).first()

        if existing:
            skipped += 1
            continue

        Contribution.objects.create(
            group=group,
            member=member,
            amount=amount,
            date=datetime.utcnow(),
            source=import_request.source,
        )
        imported += 1

    return ImportResponse(imported=imported, skipped=skipped)


class PostImportResponse(BaseModel):
    posts_imported: int
    payments_found: int
    collections_found: int
    messages_found: int


@router.post("/import-posts", response_model=PostImportResponse)
def import_whatsapp_posts(
    group_id: int,
    file: UploadFile = File(...),
    user=Depends(get_user_or_403),
):
    """Import WhatsApp chat as Posts"""
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")

    content = file.file.read().decode("utf-8", errors="ignore")
    posts = parse_whatsapp_posts(content)

    posts_imported = 0
    payments_found = 0
    collections_found = 0
    messages_found = 0

    for wp in posts:
        post_type_map = {
            "payment": "post",
            "collection": "post",
            "order": "post",
            "rule": "message",
            "message": "message",
        }

        WhatsAppPost.objects.create(
            group=group,
            user=user if hasattr(user, 'id') else None,
            sender=wp.sender,
            content=wp.content,
            post_type=post_type_map.get(wp.post_type, "message"),
            timestamp=wp.timestamp or datetime.utcnow(),
            raw_members=wp.raw_members,
            raw_line=wp.raw_line,
        )
        posts_imported += 1

        if wp.post_type == "payment":
            payments_found += 1
        elif wp.post_type == "collection":
            collections_found += 1
        else:
            messages_found += 1

    return PostImportResponse(
        posts_imported=posts_imported,
        payments_found=payments_found,
        collections_found=collections_found,
        messages_found=messages_found,
    )


class ConvertResponse(BaseModel):
    contributions_created: int
    payouts_created: int
    unmatched: List[dict]


@router.post("/convert-posts", response_model=ConvertResponse)
def convert_posts_to_contributions(
    group_id: int,
    user=Depends(get_user_or_403),
):
    """Convert payment posts to Contributions and Payouts"""
    try:
        group = SavingsGroup.objects.get(id=group_id)
    except SavingsGroup.DoesNotExist:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.created_by != user:
        raise HTTPException(status_code=403, detail="Not authorized")

    members = GroupMember.objects.filter(group_id=group_id)
    member_names = [m.alias for m in members]
    member_by_alias = {m.alias: m for m in members}

    payment_posts = WhatsAppPost.objects.filter(
        group_id=group_id,
        post_type="post"
    )

    contributions_created = 0
    payouts_created = 0
    unmatched = []

    for post in payment_posts:
        if not post.raw_members:
            continue

        raw_members = post.raw_members if isinstance(post.raw_members, list) else []
        if not raw_members:
            continue

        for rm in raw_members:
            whatsapp_name = rm.get("name", "")
            if not whatsapp_name:
                continue

            matched_name = fuzzy_match_member(whatsapp_name, member_names)
            if not matched_name:
                unmatched.append({"whatsapp": whatsapp_name, "post_id": post.id})
                continue

            member = member_by_alias.get(matched_name)
            if not member:
                continue

            existing_contrib = Contribution.objects.filter(
                group_id=group_id,
                member_id=member.id,
            ).first()

            if not existing_contrib:
                Contribution.objects.create(
                    group=group,
                    member=member,
                    amount=group.contribution_amount,
                    date=post.timestamp,
                    source="whatsapp_import",
                )
                contributions_created += 1

            if rm.get("received_payout"):
                existing_payout = Payout.objects.filter(
                    group_id=group_id,
                    member_id=member.id,
                    cycle_number=group.current_cycle_number,
                ).first()

                if not existing_payout:
                    Payout.objects.create(
                        group=group,
                        member=member,
                        cycle_number=group.current_cycle_number,
                        amount=group.contribution_amount * members.count(),
                        payout_date=post.timestamp,
                    )
                    payouts_created += 1

    return ConvertResponse(
        contributions_created=contributions_created,
        payouts_created=payouts_created,
        unmatched=unmatched,
    )