# AjoGo Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete FastAPI + Supabase backend for the AjoGo digital thrift platform, enabling admins to manage groups, track contributions, send WhatsApp reminders, and handle payout cycles.

**Architecture:** REST API with Supabase backend (PostgreSQL), Supabase Auth for admin authentication, Twilio WhatsApp API for member notifications, Vercel Cron for scheduled reminder jobs.

**Tech Stack:** FastAPI, Supabase (PostgreSQL + Auth), Twilio WhatsApp API, Pydantic, SQLAlchemy (via Supabase)

---

## File Structure

```
api/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── groups.py      # Group CRUD endpoints
│   │       ├── members.py     # Member CRUD endpoints  
│   │       ├── contributions.py  # Contribution endpoints
│   │       ├── payouts.py     # Payout endpoints
│   │       ├── reminders.py   # Reminder endpoints
│   │       ├── whatsapp.py    # WhatsApp import/notify
│   │       └── cron.py        # Cron job endpoints
│   ├── core/
│   │   ├── config.py          # Environment config
│   │   └── security.py        # Auth utilities
│   ├── db/
│   │   ├── models.py          # SQLAlchemy models
│   │   ├── schemas.py         # Pydantic schemas
│   │   └── migrations/        # Database migrations
│   ├── services/
│   │   ├── contributions.py  # Contribution business logic
│   │   ├── payouts.py         # Payout cycle logic
│   │   ├── reminders.py       # Reminder scheduling
│   │   └── whatsapp.py       # Twilio client + parser
│   └── main.py               # FastAPI app entry
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_whatsapp_parser.py
│   ├── test_payout_service.py
│   ├── test_contributions.py
│   ├── test_reminders.py
│   ├── test_auth.py
│   └── test_api_groups.py
└── e2e/
    ├── test_whatsapp_import.py
    └── test_payout_cycle.py
```

---

## Phase 1: Foundation

### Task 1: Project Setup & Configuration

**Files:**
- Create: `api/app/core/config.py`
- Create: `api/app/core/security.py`
- Create: `api/app/db/models.py`
- Create: `api/app/db/schemas.py`
- Create: `api/app/main.py`
- Create: `api/tests/conftest.py`
- Modify: `api/pyproject.toml`

- [ ] **Step 1: Write config module**

```python
# api/app/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    supabase_service_key: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_whatsapp_from: str
    cron_secret: str
    app_url: str = "http://localhost:8000"
    
    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Write security module**

```python
# api/app/core/security.py
from supabase import create_client, Client
from app.core.config import get_settings

def get_supabase_client() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_anon_key)

def get_supabase_admin() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)
```

- [ ] **Step 3: Write SQLAlchemy models**

```python
# api/app/db/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(String, nullable=False)  # Supabase user ID
    name = Column(String, nullable=False)
    contribution_amount = Column(Integer, nullable=False)
    payout_schedule = Column(String, nullable=False)  # weekly, monthly
    current_cycle_number = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    members = relationship("Member", back_populates="group")
    contributions = relationship("Contribution", back_populates="group")
    payouts = relationship("Payout", back_populates="group")

class Member(Base):
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    phone = Column(String, nullable=False)
    name = Column(String, nullable=False)
    rotation_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    group = relationship("Group", back_populates="members")
    contributions = relationship("Contribution", back_populates="member")
    payouts = relationship("Payout", back_populates="member")

class Contribution(Base):
    __tablename__ = "contributions"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    source = Column(String, default="manual")  # 'manual' or 'whatsapp_import'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    member = relationship("Member", back_populates="contributions")
    group = relationship("Group", back_populates="contributions")

class ReminderState(Base):
    __tablename__ = "reminder_states"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    cycle_number = Column(Integer, nullable=False)
    last_reminder_sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReminderRule(Base):
    __tablename__ = "reminder_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    days_before_payout = Column(Integer, default=3)
    message = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Payout(Base):
    __tablename__ = "payouts"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    cycle_number = Column(Integer, nullable=False)
    amount = Column(Integer, nullable=False)
    payout_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    group = relationship("Group", back_populates="payouts")
    member = relationship("Member", back_populates="payouts")
```

- [ ] **Step 4: Write Pydantic schemas**

```python
# api/app/db/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class GroupBase(BaseModel):
    name: str
    contribution_amount: int
    payout_schedule: str

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    contribution_amount: Optional[int] = None
    payout_schedule: Optional[str] = None
    current_cycle_number: Optional[int] = None

class GroupResponse(GroupBase):
    id: int
    admin_id: str
    current_cycle_number: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class MemberBase(BaseModel):
    phone: str
    name: str
    rotation_order: int

class MemberCreate(MemberBase):
    pass

class MemberResponse(MemberBase):
    id: int
    group_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ContributionBase(BaseModel):
    amount: int
    date: datetime

class ContributionCreate(ContributionBase):
    member_id: int

class ContributionResponse(ContributionBase):
    id: int
    member_id: int
    group_id: int
    source: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class PayoutBase(BaseModel):
    member_id: int
    amount: int
    payout_date: datetime

class PayoutCreate(PayoutBase):
    pass

class PayoutResponse(PayoutBase):
    id: int
    group_id: int
    cycle_number: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ReminderRuleBase(BaseModel):
    days_before_payout: int = 3
    message: str
    is_active: bool = True

class ReminderRuleCreate(ReminderRuleBase):
    pass

class ReminderRuleResponse(ReminderRuleBase):
    id: int
    group_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# WhatsApp import schemas
class ParsedContribution(BaseModel):
    amount: int
    sender: Optional[str] = None
    confidence: float = 1.0
    needs_review: bool = False
    raw_message: str

class WhatsAppImportRequest(BaseModel):
    group_id: int
    messages: list[str]

class WhatsAppImportResponse(BaseModel):
    parsed_contributions: list[ParsedContribution]
    total_lines: int
    parsed_count: int
```

- [ ] **Step 5: Write FastAPI main app**

```python
# api/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AjoGo API",
    description="Digital Savings & Thrift Platform API",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.app_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}
```

- [ ] **Step 6: Write pytest conftest**

```python
# api/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base
from app.main import app
from app.core.security import get_supabase_client

# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def mock_supabase(monkeypatch):
    class MockClient:
        pass
    
    monkeypatch.setattr("app.core.security.get_supabase_client", lambda: MockClient())
    monkeypatch.setattr("app.core.security.get_supabase_admin", lambda: MockClient())
```

- [ ] **Step 7: Commit**

```bash
git add api/app/core api/app/db api/tests/conftest.py api/app/main.py api/pyproject.toml
git commit -m "feat: add project foundation - config, models, schemas, FastAPI app"
```

---

### Task 2: Database Migrations & Supabase Setup

**Files:**
- Create: `api/app/db/migrations/env.py`
- Create: `api/app/db/migrations/versions/001_initial.py`
- Modify: `api/app/db/models.py` (add RLS)

- [ ] **Step 1: Write Alembic config**

```python
# api/app/db/migrations/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.models import Base
from app.core.config import get_settings

config = context.config
settings = get_settings()

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url():
    return f"postgresql://:@localhost/ajogo"

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 2: Write initial migration**

```python
# api/app/db/migrations/versions/001_initial.py
"""initial migration

Revision ID: 001
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('groups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('admin_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('contribution_amount', sa.Integer(), nullable=False),
        sa.Column('payout_schedule', sa.String(), nullable=False),
        sa.Column('current_cycle_number', sa.Integer(), nullable=True, default=1),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_groups_id'), 'groups', ['id'], unique=False)
    
    op.create_table('members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('phone', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('rotation_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_members_id'), 'members', ['id'], unique=False)
    
    op.create_table('contributions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('source', sa.String(), nullable=True, default='manual'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contributions_id'), 'contributions', ['id'], unique=False)
    
    op.create_table('reminder_states',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('cycle_number', sa.Integer(), nullable=False),
        sa.Column('last_reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('reminder_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('days_before_payout', sa.Integer(), nullable=True, default=3),
        sa.Column('message', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('payouts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('cycle_number', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('payout_date', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['groups.id'], ),
        sa.ForeignKeyConstraint(['member_id'], ['members.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payouts_id'), 'payouts', ['id'], unique=False)

def downgrade() -> None:
    op.drop_table('payouts')
    op.drop_table('reminder_rules')
    op.drop_table('reminder_states')
    op.drop_table('contributions')
    op.drop_table('members')
    op.drop_table('groups')
```

- [ ] **Step 3: Add Supabase RLS policies**

```python
# Add to migration - RLS policies for Supabase
# Enable RLS
op.execute('ALTER TABLE groups ENABLE ROW LEVEL SECURITY')
op.execute('ALTER TABLE members ENABLE ROW LEVEL SECURITY')
op.execute('ALTER TABLE contributions ENABLE ROW LEVEL SECURITY')
op.execute('ALTER TABLE reminder_states ENABLE ROW LEVEL SECURITY')
op.execute('ALTER TABLE reminder_rules ENABLE ROW LEVEL SECURITY')
op.execute('ALTER TABLE payouts ENABLE ROW LEVEL SECURITY')

# Admin can only see their own groups
op.execute('''CREATE POLICY "admins_can_manage_groups" ON groups
    FOR ALL USING (auth.uid() = admin_id)''')

# Similar for other tables via FK to groups
```

- [ ] **Step 4: Commit**

```bash
git add api/app/db/migrations
git commit -m "feat: add database migrations with Supabase RLS policies"
```

---

## Phase 2: Core API

### Task 3: Groups API

**Files:**
- Create: `api/app/api/routes/groups.py`
- Modify: `api/app/main.py`

- [ ] **Step 1: Write Groups API**

```python
# api/app/api/routes/groups.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.schemas import GroupCreate, GroupUpdate, GroupResponse
from app.db.models import Group
from app.core.security import get_supabase_admin

router = APIRouter(prefix="/groups", tags=["groups"])

def get_db():
    # Will be implemented with Supabase client
    pass

@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
def create_group(
    group: GroupCreate,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    db_group = Group(
        admin_id=user.id,
        name=group.name,
        contribution_amount=group.contribution_amount,
        payout_schedule=group.payout_schedule,
        current_cycle_number=1
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

@router.get("/", response_model=List[GroupResponse])
def list_groups(
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    groups = db.query(Group).filter(Group.admin_id == user.id).all()
    return groups

@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.admin_id == user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group

@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    group_update: GroupUpdate,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.admin_id == user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    update_data = group_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(group, field, value)
    
    db.commit()
    db.refresh(group)
    return group

@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.admin_id == user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    db.delete(group)
    db.commit()
    return None
```

- [ ] **Step 2: Register router in main.py**

```python
# api/app/main.py additions
from app.api.routes import groups, members, contributions, payouts, reminders, whatsapp, cron

app.include_router(groups.router, prefix="/api")
# ... other routers
```

- [ ] **Step 3: Run tests and fix**

Run: `pytest api/tests/test_api_groups.py -v`

- [ ] **Step 4: Commit**

```bash
git add api/app/api/routes/groups.py api/app/main.py
git commit -m "feat: add Groups CRUD API endpoints"
```

---

### Task 4: Members API

**Files:**
- Create: `api/app/api/routes/members.py`

- [ ] **Step 1: Write Members API**

```python
# api/app/api/routes/members.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.schemas import MemberCreate, MemberResponse
from app.db.models import Member, Group
from app.core.security import get_supabase_admin

router = APIRouter(prefix="/groups/{group_id}/members", tags=["members"])

def get_db():
    pass

def verify_group_access(group_id: int, db: Session, supabase) -> Group:
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.admin_id == user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=403, detail="Not authorized to access this group")
    return group

@router.post("/", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    group_id: int,
    member: MemberCreate,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    
    db_member = Member(
        group_id=group_id,
        phone=member.phone,
        name=member.name,
        rotation_order=member.rotation_order
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

@router.get("/", response_model=List[MemberResponse])
def list_members(
    group_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    members = db.query(Member).filter(Member.group_id == group_id).order_by(Member.rotation_order).all()
    return members

@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    group_id: int,
    member_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    
    member = db.query(Member).filter(
        Member.id == member_id,
        Member.group_id == group_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    db.delete(member)
    db.commit()
    return None
```

- [ ] **Step 2: Commit**

```bash
git add api/app/api/routes/members.py
git commit -m "feat: add Members API endpoints"
```

---

### Task 5: Contributions API

**Files:**
- Create: `api/app/api/routes/contributions.py`

- [ ] **Step 1: Write Contributions API**

```python
# api/app/api/routes/contributions.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from app.db.schemas import ContributionCreate, ContributionResponse
from app.db.models import Contribution, Member, Group
from app.core.security import get_supabase_admin

router = APIRouter(prefix="/groups/{group_id}/contributions", tags=["contributions"])

def get_db():
    pass

def verify_group_access(group_id: int, db: Session, supabase):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.admin_id == user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=403, detail="Not authorized to access this group")
    return group

@router.post("/", response_model=ContributionResponse, status_code=status.HTTP_201_CREATED)
def create_contribution(
    group_id: int,
    contribution: ContributionCreate,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    
    # Validate amount
    if contribution.amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be positive")
    
    # Validate date - not in the future
    if contribution.date > datetime.now() + timedelta(days=1):
        raise HTTPException(status_code=422, detail="Date cannot be in the future")
    
    # Validate member belongs to group
    member = db.query(Member).filter(
        Member.id == contribution.member_id,
        Member.group_id == group_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=403, detail="Member not found in this group")
    
    # Check for duplicate (same member, date, amount)
    existing = db.query(Contribution).filter(
        Contribution.member_id == contribution.member_id,
        Contribution.group_id == group_id,
        Contribution.date == contribution.date,
        Contribution.amount == contribution.amount
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="Duplicate contribution detected")
    
    db_contribution = Contribution(
        member_id=contribution.member_id,
        group_id=group_id,
        amount=contribution.amount,
        date=contribution.date,
        source="manual"
    )
    db.add(db_contribution)
    db.commit()
    db.refresh(db_contribution)
    return db_contribution

@router.get("/", response_model=List[ContributionResponse])
def list_contributions(
    group_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    contributions = db.query(Contribution).filter(Contribution.group_id == group_id).order_by(Contribution.date.desc()).all()
    return contributions
```

- [ ] **Step 2: Commit**

```bash
git add api/app/api/routes/contributions.py
git commit -m "feat: add Contributions API endpoints"
```

---

### Task 6: Payouts API

**Files:**
- Create: `api/app/api/routes/payouts.py`

- [ ] **Step 1: Write Payouts API**

```python
# api/app/api/routes/payouts.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.db.schemas import PayoutCreate, PayoutResponse
from app.db.models import Payout, Member, Group
from app.core.security import get_supabase_admin

router = APIRouter(prefix="/groups/{group_id}/payouts", tags=["payouts"])

def get_db():
    pass

def verify_group_access(group_id: int, db: Session, supabase):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.admin_id == user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=403, detail="Not authorized to access this group")
    return group

@router.post("/", response_model=PayoutResponse, status_code=status.HTTP_201_CREATED)
def create_payout(
    group_id: int,
    payout: PayoutCreate,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    
    # Validate member belongs to group
    member = db.query(Member).filter(
        Member.id == payout.member_id,
        Member.group_id == group_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=403, detail="Member not found in this group")
    
    db_payout = Payout(
        group_id=group_id,
        member_id=payout.member_id,
        cycle_number=group.current_cycle_number,
        amount=payout.amount,
        payout_date=payout.payout_date
    )
    db.add(db_payout)
    db.commit()
    db.refresh(db_payout)
    return db_payout

@router.get("/", response_model=List[PayoutResponse])
def list_payouts(
    group_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    payouts = db.query(Payout).filter(Payout.group_id == group_id).order_by(Payout.payout_date.desc()).all()
    return payouts
```

- [ ] **Step 2: Commit**

```bash
git add api/app/api/routes/payouts.py
git commit -m "feat: add Payouts API endpoints"
```

---

### Task 7: Reminders API

**Files:**
- Create: `api/app/api/routes/reminders.py`

- [ ] **Step 1: Write Reminders API**

```python
# api/app/api/routes/reminders.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.schemas import ReminderRuleCreate, ReminderRuleResponse
from app.db.models import ReminderRule, Group
from app.core.security import get_supabase_admin

router = APIRouter(prefix="/groups/{group_id}/reminders", tags=["reminders"])

def get_db():
    pass

def verify_group_access(group_id: int, db: Session, supabase):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.admin_id == user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=403, detail="Not authorized to access this group")
    return group

@router.post("/rules", response_model=ReminderRuleResponse, status_code=status.HTTP_201_CREATED)
def create_reminder_rule(
    group_id: int,
    rule: ReminderRuleCreate,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    
    db_rule = ReminderRule(
        group_id=group_id,
        days_before_payout=rule.days_before_payout,
        message=rule.message,
        is_active=rule.is_active
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule

@router.get("/rules", response_model=List[ReminderRuleResponse])
def list_reminder_rules(
    group_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    rules = db.query(ReminderRule).filter(ReminderRule.group_id == group_id).all()
    return rules

@router.patch("/rules/{rule_id}", response_model=ReminderRuleResponse)
def update_reminder_rule(
    group_id: int,
    rule_id: int,
    rule_update: ReminderRuleCreate,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    group = verify_group_access(group_id, db, supabase)
    
    rule = db.query(ReminderRule).filter(
        ReminderRule.id == rule_id,
        ReminderRule.group_id == group_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Reminder rule not found")
    
    rule.days_before_payout = rule_update.days_before_payout
    rule.message = rule_update.message
    rule.is_active = rule_update.is_active
    
    db.commit()
    db.refresh(rule)
    return rule
```

- [ ] **Step 2: Commit**

```bash
git add api/app/api/routes/reminders.py
git commit -m "feat: add Reminders API endpoints"
```

---

## Phase 3: Business Logic Services

### Task 8: Payout Cycle Service

**Files:**
- Create: `api/app/services/payouts.py`

- [ ] **Step 1: Write payout cycle service**

```python
# api/app/services/payouts.py
from sqlalchemy.orm import Session
from app.db.models import Group, Member, Contribution, Payout
from typing import Optional

class PayoutService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_next_recipient(self, group_id: int, cycle_number: int) -> Optional[Member]:
        """Get the next member who should receive payout in this cycle."""
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return None
        
        members = self.db.query(Member).filter(
            Member.group_id == group_id
        ).order_by(Member.rotation_order).all()
        
        if not members:
            return None
        
        # Get all members who already received payout this cycle
        paid_member_ids = set(
            p.member_id for p in self.db.query(Payout).filter(
                Payout.group_id == group_id,
                Payout.cycle_number == cycle_number
            ).all()
        )
        
        # Find first member not in paid list
        for member in members:
            if member.id not in paid_member_ids:
                return member
        
        return None  # All members paid this cycle
    
    def calculate_payout_amount(self, group_id: int) -> int:
        """Calculate payout amount: all contributions for current cycle."""
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return 0
        
        # Sum all contributions for current cycle
        # Note: contributions don't have cycle number, so we use all contributions
        total = self.db.query(Contribution).filter(
            Contribution.group_id == group_id
        ).count()
        
        return group.contribution_amount * total
    
    def advance_cycle(self, group_id: int) -> int:
        """Advance to next cycle after all members have been paid."""
        group = self.db.query(Group).filter(Group.id == group_id).first()
        if not group:
            return None
        
        # Check if all members have been paid
        members_count = self.db.query(Member).filter(Member.group_id == group_id).count()
        paid_count = self.db.query(Payout).filter(
            Payout.group_id == group_id,
            Payout.cycle_number == group.current_cycle_number
        ).count()
        
        if members_count > 0 and paid_count >= members_count:
            group.current_cycle_number += 1
            self.db.commit()
            return group.current_cycle_number
        
        return group.current_cycle_number
    
    def is_cycle_complete(self, group_id: int, cycle_number: int) -> bool:
        """Check if all members have received payout for given cycle."""
        members_count = self.db.query(Member).filter(Member.group_id == group_id).count()
        paid_count = self.db.query(Payout).filter(
            Payout.group_id == group_id,
            Payout.cycle_number == cycle_number
        ).count()
        
        return members_count > 0 and paid_count >= members_count
```

- [ ] **Step 2: Add endpoint to use service**

```python
# In api/app/api/routes/payouts.py, add:
@router.get("/next-recipient")
def get_next_recipient(
    group_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    from app.services.payouts import PayoutService
    group = verify_group_access(group_id, db, supabase)
    
    service = PayoutService(db)
    recipient = service.get_next_recipient(group_id, group.current_cycle_number)
    
    if not recipient:
        return {"recipient": None, "cycle_complete": True}
    
    return {
        "recipient": MemberResponse.model_validate(recipient),
        "cycle_complete": False
    }

@router.post("/{group_id}/advance-cycle")
def post_advance_cycle(
    group_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    from app.services.payouts import PayoutService
    group = verify_group_access(group_id, db, supabase)
    
    service = PayoutService(db)
    new_cycle = service.advance_cycle(group_id)
    
    return {"new_cycle_number": new_cycle}
```

- [ ] **Step 3: Commit**

```bash
git add api/app/services/payouts.py api/app/api/routes/payouts.py
git commit -m "feat: add payout cycle service with rotation logic"
```

---

### Task 9: Reminder Service

**Files:**
- Create: `api/app/services/reminders.py`

- [ ] **Step 1: Write reminder service**

```python
# api/app/services/reminders.py
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from app.db.models import Group, Member, ReminderRule, ReminderState
from typing import List, Tuple

class ReminderService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_pending_reminders(self) -> List[Tuple[Group, Member, ReminderRule]]:
        """Get all groups/members that need reminders."""
        reminders = []
        
        # Get all active groups
        groups = self.db.query(Group).all()
        
        for group in groups:
            # Get active reminder rule
            rule = self.db.query(ReminderRule).filter(
                ReminderRule.group_id == group.id,
                ReminderRule.is_active == True
            ).first()
            
            if not rule:
                continue
            
            # Check if reminder already sent today
            today = datetime.now().date()
            state = self.db.query(ReminderState).filter(
                ReminderState.group_id == group.id,
                ReminderState.cycle_number == group.current_cycle_number
            ).first()
            
            if state and state.last_reminder_sent_at:
                if state.last_reminder_sent_at.date() >= today:
                    continue  # Already sent today
            
            # Get next recipient
            from app.services.payouts import PayoutService
            payout_service = PayoutService(self.db)
            recipient = payout_service.get_next_recipient(group.id, group.current_cycle_number)
            
            if recipient:
                reminders.append((group, recipient, rule))
        
        return reminders
    
    def mark_reminder_sent(self, group_id: int, cycle_number: int) -> None:
        """Mark that a reminder was sent for this cycle."""
        state = self.db.query(ReminderState).filter(
            ReminderState.group_id == group_id,
            ReminderState.cycle_number == cycle_number
        ).first()
        
        if not state:
            state = ReminderState(
                group_id=group_id,
                cycle_number=cycle_number,
                last_reminder_sent_at=datetime.now()
            )
            self.db.add(state)
        else:
            state.last_reminder_sent_at = datetime.now()
        
        self.db.commit()
    
    def send_whatsapp_reminder(self, group: Group, member: Member, rule: ReminderRule) -> bool:
        """Send WhatsApp reminder to member. Returns success status."""
        from app.services.whatsapp import WhatsAppService
        
        whatsapp = WhatsAppService()
        message = rule.message.format(
            member_name=member.name,
            group_name=group.name,
            amount=group.contribution_amount,
            cycle=group.current_cycle_number
        )
        
        return whatsapp.send_message(member.phone, message)
```

- [ ] **Step 2: Commit**

```bash
git add api/app/services/reminders.py
git commit -m "feat: add reminder scheduling service"
```

---

## Phase 4: WhatsApp Integration

### Task 10: Twilio WhatsApp Client

**Files:**
- Create: `api/app/services/whatsapp.py`

- [ ] **Step 1: Write WhatsApp service**

```python
# api/app/services/whatsapp.py
from twilio.rest import Client
from app.core.config import get_settings

class WhatsAppService:
    def __init__(self):
        settings = get_settings()
        self.client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        self.from_number = settings.twilio_whatsapp_from
    
    def send_message(self, to: str, body: str) -> bool:
        """Send WhatsApp message. Returns True if successful."""
        try:
            # Format phone number for WhatsApp
            if not to.startswith("whatsapp:"):
                to = f"whatsapp:{to}"
            
            message = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=to
            )
            return message.sid is not None
        except Exception as e:
            print(f"Failed to send WhatsApp message: {e}")
            return False
```

- [ ] **Step 2: Commit**

```bash
git add api/app/services/whatsapp.py
git commit -m "feat: add Twilio WhatsApp client service"
```

---

### Task 11: WhatsApp Parser

**Files:**
- Create: `api/app/services/whatsapp_parser.py`

- [ ] **Step 1: Write parser with regex patterns**

```python
# api/app/services/whatsapp_parser.py
import re
from typing import Optional
from app.db.schemas import ParsedContribution
from datetime import datetime

class WhatsAppParser:
    """Parse WhatsApp chat export for contribution messages."""
    
    # Patterns for different message formats
    PATTERNS = [
        # "12/03/2025, 08:30 - Chidi: paid 5000"
        re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4}),?\s*(\d{1,2}:\d{2})\s*-\s*([^:]+):\s*paid\s*([\d,]+)', re.IGNORECASE),
        # "12/03/2025, 09:15 - Mary: 3000"
        re.compile(r'(\d{1,2}/\d{1,2}/\d{2,4}),?\s*(\d{1,2}:\d{2})\s*-\s*([^:]+):\s*([\d,]+)'),
        # "Nurse Ada: contributed N10,000"
        re.compile(r'^([^:]+):\s*contributed\s*N?([\d,]+)', re.IGNORECASE),
        # "Emeka 💰: transferred 5,000"
        re.compile(r'^([^💰]+)[\s💰]*:\s*transferred\s*([\d,]+)', re.IGNORECASE),
        # "John: 5000" (just amount)
        re.compile(r'^([^:]+):\s*([\d,]+)$'),
    ]
    
    def parse_amount(self, amount_str: str) -> Optional[int]:
        """Convert various amount formats to integer."""
        # Remove commas, N prefix, k suffix
        amount_str = amount_str.replace(",", "").strip()
        amount_str = amount_str.replace("N", "").strip()
        
        if amount_str.lower() == "k":
            return None  # Need review
        
        if amount_str.lower().endswith("k"):
            try:
                return int(float(amount_str[:-1]) * 1000)
            except:
                return None
        
        # Handle written numbers (basic)
        written_numbers = {
            "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
            "five thousand": 5000, "ten thousand": 10000
        }
        if amount_str.lower() in written_numbers:
            return written_numbers[amount_str.lower()]
        
        try:
            value = int(float(amount_str))
            if value <= 0:
                return None
            return value
        except:
            return None
    
    def parse_line(self, line: str) -> Optional[ParsedContribution]:
        """Parse a single line from WhatsApp export."""
        line = line.strip()
        if not line:
            return None
        
        # Try each pattern
        for i, pattern in enumerate(self.PATTERNS):
            match = pattern.match(line)
            if match:
                sender = match.group(1).strip()
                amount_str = match.group(2).strip() if len(match.groups()) >= 2 else ""
                
                # Confidence based on pattern specificity
                if i == 0:  # "paid 5000" - high confidence
                    confidence = 0.9
                elif i <= 2:  # Has sender and amount
                    confidence = 0.8
                else:
                    confidence = 0.5
                
                amount = self.parse_amount(amount_str)
                if amount is None:
                    return ParsedContribution(
                        amount=0,
                        sender=sender,
                        confidence=0.2,
                        needs_review=True,
                        raw_message=line
                    )
                
                return ParsedContribution(
                    amount=amount,
                    sender=sender,
                    confidence=confidence,
                    needs_review=confidence < 0.7,
                    raw_message=line
                )
        
        # Check for standalone amount
        amount = self.parse_amount(line)
        if amount and amount > 0:
            return ParsedContribution(
                amount=amount,
                sender=None,
                confidence=0.2,
                needs_review=True,
                raw_message=line
            )
        
        return None
    
    def parse_messages(self, messages: list[str]) -> list[ParsedContribution]:
        """Parse multiple lines of WhatsApp export."""
        results = []
        for line in messages:
            parsed = self.parse_line(line)
            if parsed:
                results.append(parsed)
        return results
```

- [ ] **Step 2: Commit**

```bash
git add api/app/services/whatsapp_parser.py
git commit -m "feat: add WhatsApp message parser with regex patterns"
```

---

### Task 12: WhatsApp Import API

**Files:**
- Create: `api/app/api/routes/whatsapp.py`

- [ ] **Step 1: Write WhatsApp import endpoint**

```python
# api/app/api/routes/whatsapp.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.schemas import WhatsAppImportRequest, WhatsAppImportResponse, ParsedContribution, ContributionCreate
from app.db.models import Group, Member, Contribution
from app.core.security import get_supabase_admin
from app.services.whatsapp_parser import WhatsAppParser
from datetime import datetime

router = APIRouter(prefix="/groups/{group_id}/whatsapp", tags=["whatsapp"])

def get_db():
    pass

def verify_group_access(group_id: int, db: Session, supabase):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.admin_id == user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=403, detail="Not authorized to access this group")
    return group

@router.post("/import", response_model=WhatsAppImportResponse)
def import_contributions(
    group_id: int,
    request: WhatsAppImportRequest,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    """Parse WhatsApp messages and return parsed contributions for review."""
    group = verify_group_access(group_id, db, supabase)
    
    parser = WhatsAppParser()
    parsed = parser.parse_messages(request.messages)
    
    return WhatsAppImportResponse(
        parsed_contributions=parsed,
        total_lines=len(request.messages),
        parsed_count=len(parsed)
    )

@router.post("/import/confirm")
def confirm_import(
    group_id: int,
    contributions: List[ContributionCreate],
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    """Import confirmed contributions to database."""
    group = verify_group_access(group_id, db, supabase)
    
    imported = []
    for contrib in contributions:
        # Verify member belongs to group
        member = db.query(Member).filter(
            Member.id == contrib.member_id,
            Member.group_id == group_id
        ).first()
        
        if not member:
            continue
        
        db_contrib = Contribution(
            member_id=contrib.member_id,
            group_id=group_id,
            amount=contrib.amount,
            date=contrib.date,
            source="whatsapp_import"
        )
        db.add(db_contrib)
        imported.append(db_contrib)
    
    db.commit()
    
    return {"imported_count": len(imported)}
```

- [ ] **Step 2: Commit**

```bash
git add api/app/api/routes/whatsapp.py
git commit -m "feat: add WhatsApp import endpoints"
```

---

## Phase 5: External Integrations

### Task 13: Cron Endpoint

**Files:**
- Create: `api/app/api/routes/cron.py`

- [ ] **Step 1: Write cron endpoint for reminders**

```python
# api/app/api/routes/cron.py
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from app.core.config import get_settings
from app.db.models import Group
from app.services.reminders import ReminderService

router = APIRouter(prefix="/cron", tags=["cron"])

def get_db():
    pass

def verify_cron_secret(x_cron_secret: Optional[str] = Header(None)):
    settings = get_settings()
    if x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")
    return True

@router.post("/send-reminders")
def send_reminders(
    authorized: bool = Depends(verify_cron_secret),
    db: Session = Depends(get_db)
):
    """Send pending WhatsApp reminders. Called by Vercel Cron every 15 min."""
    reminder_service = ReminderService(db)
    pending = reminder_service.get_pending_reminders()
    
    sent_count = 0
    failed_count = 0
    
    for group, member, rule in pending:
        success = reminder_service.send_whatsapp_reminder(group, member, rule)
        if success:
            reminder_service.mark_reminder_sent(group.id, group.current_cycle_number)
            sent_count += 1
        else:
            failed_count += 1
    
    return {
        "status": "completed",
        "reminders_due": len(pending),
        "sent": sent_count,
        "failed": failed_count
    }
```

- [ ] **Step 2: Add Vercel cron config**

```json
// vercel.json
{
  "crons": [
    {
      "path": "/api/cron/send-reminders",
      "schedule": "*/15 * * * *"
    }
  ]
}
```

- [ ] **Step 3: Commit**

```bash
git add api/app/api/routes/cron.py
git commit -m "feat: add cron endpoint for scheduled reminders"
```

---

### Task 14: CSV Export

**Files:**
- Create: `api/app/api/routes/export.py`

- [ ] **Step 1: Write CSV export endpoint**

```python
# api/app/api/routes/export.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv
import io
from app.db.models import Group, Member, Contribution
from app.core.security import get_supabase_admin

router = APIRouter(prefix="/groups/{group_id}/export", tags=["export"])

def get_db():
    pass

def verify_group_access(group_id: int, db: Session, supabase):
    user = supabase.auth.get_user()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    group = db.query(Group).filter(
        Group.id == group_id,
        Group.admin_id == user.id
    ).first()
    
    if not group:
        raise HTTPException(status_code=403, detail="Not authorized to access this group")
    return group

@router.get("/csv")
def export_csv(
    group_id: int,
    db: Session = Depends(get_db),
    supabase = Depends(get_supabase_admin)
):
    """Export group contributions as CSV."""
    group = verify_group_access(group_id, db, supabase)
    
    contributions = db.query(Contribution).filter(
        Contribution.group_id == group_id
    ).order_by(Contribution.date).all()
    
    # Build member lookup
    members = {m.id: m.name for m in db.query(Member).filter(Member.group_id == group_id).all()}
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Member", "Amount", "Source"])
    
    for contrib in contributions:
        writer.writerow([
            contrib.date.strftime("%Y-%m-%d"),
            members.get(contrib.member_id, "Unknown"),
            contrib.amount,
            contrib.source
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={group.name}_contributions.csv"}
    )
```

- [ ] **Step 2: Commit**

```bash
git add api/app/api/routes/export.py
git commit -m "feat: add CSV export endpoint"
```

---

## Summary

**Total Tasks:** 14 tasks across 5 phases

**Phase 1 (Foundation):** Tasks 1-2
- Project setup, config, models, schemas, migrations

**Phase 2 (Core API):** Tasks 3-7
- Groups, Members, Contributions, Payouts, Reminders CRUD

**Phase 3 (Business Logic):** Tasks 8-9
- Payout cycle service, Reminder scheduling service

**Phase 4 (WhatsApp):** Tasks 10-12
- Twilio client, Parser, Import flow

**Phase 5 (External):** Tasks 13-14
- Cron endpoint, CSV export

**Execution approach:**
- Each task is 2-5 minutes of work
- Run tests after each task
- Commit after each task passes

**Next step:** Choose execution approach:
1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task
2. **Inline Execution** - Execute tasks in this session with checkpoints
