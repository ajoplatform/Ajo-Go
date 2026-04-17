from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session
import json

from api.app.db.database import get_db
from api.app.db.models import Group, Member, Contribution, Admin, Post
from api.app.core.auth import get_current_admin
from api.app.services.whatsapp_parser import (
    parse_file,
    WhatsAppParseResult,
    parse_whatsapp_posts,
    fuzzy_match_member,
)


router = APIRouter(
    prefix="/api/groups/{group_id}/whatsapp-import", tags=["whatsapp-import"]
)


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


def get_group_or_404(group_id: int, db: Session, admin: dict) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    admin_obj = db.query(Admin).filter(Admin.email == admin["email"]).first()
    if group.admin_id != admin_obj.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return group


@router.post("/parse", response_model=List[ParsedContribution])
def parse_whatsapp_export(
    group_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)

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
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    group = get_group_or_404(group_id, db, admin)

    imported = 0
    skipped = 0

    for contrib in import_request.contributions:
        sender = contrib.get("sender")
        amount = contrib.get("amount")

        if not sender or not amount:
            skipped += 1
            continue

        member = (
            db.query(Member)
            .filter(Member.group_id == group_id, Member.name.ilike(sender))
            .first()
        )

        if not member:
            skipped += 1
            continue

        existing = (
            db.query(Contribution)
            .filter(
                Contribution.group_id == group_id,
                Contribution.member_id == member.id,
                Contribution.amount == amount,
            )
            .first()
        )

        if existing:
            skipped += 1
            continue

        db_contribution = Contribution(
            group_id=group_id,
            member_id=member.id,
            amount=amount,
            date=datetime.utcnow(),
            source=import_request.source,
        )
        db.add(db_contribution)
        imported += 1

    db.commit()
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
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    """Import WhatsApp chat as Posts"""
    group = get_group_or_404(group_id, db, admin)

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

        db_post = Post(
            group_id=group_id,
            sender=wp.sender,
            content=wp.content,
            post_type=post_type_map.get(wp.post_type, "message"),
            timestamp=wp.timestamp or datetime.utcnow(),
            raw_members=json.dumps(wp.raw_members) if wp.raw_members else "[]",
            raw_line=wp.raw_line,
        )
        db.add(db_post)
        posts_imported += 1

        if wp.post_type == "payment":
            payments_found += 1
        elif wp.post_type == "collection":
            collections_found += 1
        else:
            messages_found += 1

    db.commit()
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
    db: Session = Depends(get_db),
    admin: dict = Depends(get_current_admin),
):
    """Convert payment posts to Contributions and Payouts"""
    group = get_group_or_404(group_id, db, admin)

    # Get all members for this group
    members = db.query(Member).filter(Member.group_id == group_id).all()
    member_names = [m.name for m in members]
    member_by_name = {m.name: m for m in members}

    # Get payment posts that haven't been converted
    payment_posts = (
        db.query(Post).filter(Post.group_id == group_id, Post.post_type == "post").all()
    )

    contributions_created = 0
    payouts_created = 0
    unmatched = []

    for post in payment_posts:
        if not post.raw_members:
            continue

        import json

        raw_members = json.loads(post.raw_members)
        if not raw_members:
            continue

        for rm in raw_members:
            whats_app_name = rm.get("name", "")
            if not whats_app_name:
                continue

            # Fuzzy match
            matched_name = fuzzy_match_member(whats_app_name, member_names)
            if not matched_name:
                unmatched.append({"whatsapp": whats_app_name, "post_id": post.id})
                continue

            member = member_by_name.get(matched_name)
            if not member:
                continue

            # Check if contribution already exists
            existing = (
                db.query(Contribution)
                .filter(
                    Contribution.group_id == group_id,
                    Contribution.member_id == member.id,
                )
                .first()
            )

            if not existing:
                contrib = Contribution(
                    group_id=group_id,
                    member_id=member.id,
                    amount=group.contribution_amount,
                    date=post.timestamp,
                    source="whatsapp_import",
                )
                db.add(contrib)
                contributions_created += 1

            # If marked as received payout, create payout record
            if rm.get("received_payout"):
                existing_payout = (
                    db.query(Payout)
                    .filter(
                        Payout.group_id == group_id,
                        Payout.member_id == member.id,
                        Payout.cycle_number == group.current_cycle_number,
                    )
                    .first()
                )

                if not existing_payout:
                    payout = Payout(
                        group_id=group_id,
                        member_id=member.id,
                        cycle_number=group.current_cycle_number,
                        amount=group.contribution_amount * group.members.count(),
                        payout_date=post.timestamp,
                    )
                    db.add(payout)
                    payouts_created += 1

    db.commit()
    return ConvertResponse(
        contributions_created=contributions_created,
        payouts_created=payouts_created,
        unmatched=unmatched,
    )
