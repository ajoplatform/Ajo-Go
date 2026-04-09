from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    groups = relationship("Group", back_populates="admin")


class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True)
    admin_id = Column(Integer, ForeignKey("admins.id"), nullable=False)
    name = Column(String(255), nullable=False)
    contribution_amount = Column(Integer, nullable=False)
    payout_schedule = Column(String(50), default="monthly")
    current_cycle_number = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    admin = relationship("Admin", back_populates="groups")
    members = relationship(
        "Member", back_populates="group", cascade="all, delete-orphan"
    )
    contributions = relationship(
        "Contribution", back_populates="group", cascade="all, delete-orphan"
    )
    reminder_rules = relationship(
        "ReminderRule", back_populates="group", cascade="all, delete-orphan"
    )
    reminder_states = relationship(
        "ReminderState", back_populates="group", cascade="all, delete-orphan"
    )
    payouts = relationship(
        "Payout", back_populates="group", cascade="all, delete-orphan"
    )


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False)
    rotation_order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="members")
    contributions = relationship("Contribution", back_populates="member")


class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(50), default="manual")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="contributions")
    member = relationship("Member", back_populates="contributions")


class ReminderRule(Base):
    __tablename__ = "reminder_rules"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    days_before_payout = Column(Integer, default=1)
    message = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="reminder_rules")


class ReminderState(Base):
    __tablename__ = "reminder_states"

    group_id = Column(Integer, ForeignKey("groups.id"), primary_key=True)
    current_cycle_number = Column(Integer, nullable=False)
    last_reminder_sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    group = relationship("Group", back_populates="reminder_states")


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    cycle_number = Column(Integer, nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    payout_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    group = relationship("Group", back_populates="payouts")
    member = relationship("Member")
