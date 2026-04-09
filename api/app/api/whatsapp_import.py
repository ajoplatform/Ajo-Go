from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session

from api.app.db.database import get_db
from api.app.db.models import Group, Member, Contribution, Admin
from api.app.core.auth import get_current_admin
from api.app.services.whatsapp_parser import parse_file, WhatsAppParseResult


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
