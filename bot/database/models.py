from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class MentorStatus(str, enum.Enum):
    pending = "pending"
    probation = "probation"
    approved = "approved"
    rejected = "rejected"
    banned = "banned"


class NewbieStatus(str, enum.Enum):
    searching = "searching"
    in_session = "in_session"
    completed = "completed"
    banned = "banned"


class SessionStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"
    expired = "expired"


class RequestStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    expired = "expired"


class ReportStatus(str, enum.Enum):
    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


class Mentor(Base):
    __tablename__ = "mentors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    game_key: Mapped[str] = mapped_column(String(32), index=True, default="ark_se")
    game_nick: Mapped[str] = mapped_column(String(64))
    timezone: Mapped[str] = mapped_column(String(10))
    languages: Mapped[list[str]] = mapped_column(JSON, default=list)
    specializations: Mapped[list[str]] = mapped_column(JSON, default=list)
    experience: Mapped[str] = mapped_column(Text, default="")
    max_newbies: Mapped[int] = mapped_column(Integer, default=1)
    schedule: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default=MentorStatus.pending.value, index=True)
    rating: Mapped[float] = mapped_column(Float, default=0.0)
    total_sessions: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sessions: Mapped[list[MentorSession]] = relationship(back_populates="mentor")
    requests: Mapped[list[MentorRequest]] = relationship(back_populates="mentor")


class Newbie(Base):
    __tablename__ = "newbies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    game_key: Mapped[str] = mapped_column(String(32), index=True, default="ark_se")
    game_nick: Mapped[str] = mapped_column(String(64))
    timezone: Mapped[str] = mapped_column(String(10))
    language: Mapped[str] = mapped_column(String(16))
    needs: Mapped[list[str]] = mapped_column(JSON, default=list)
    comment: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), default=NewbieStatus.searching.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    sessions: Mapped[list[MentorSession]] = relationship(back_populates="newbie")
    requests: Mapped[list[MentorRequest]] = relationship(back_populates="newbie")


class MentorSession(Base):
    __tablename__ = "mentor_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("mentors.id"), index=True)
    newbie_id: Mapped[int] = mapped_column(ForeignKey("newbies.id"), index=True)
    channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default=SessionStatus.active.value, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    extended: Mapped[bool] = mapped_column(Boolean, default=False)

    mentor: Mapped[Mentor] = relationship(back_populates="sessions")
    newbie: Mapped[Newbie] = relationship(back_populates="sessions")
    reviews: Mapped[list[Review]] = relationship(back_populates="session")
    reports: Mapped[list[Report]] = relationship(back_populates="session")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("mentor_sessions.id"), index=True)
    author_id: Mapped[int] = mapped_column(BigInteger, index=True)
    target_id: Mapped[int] = mapped_column(BigInteger, index=True)
    rating: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[MentorSession] = relationship(back_populates="reviews")


class MentorRequest(Base):
    __tablename__ = "mentor_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    newbie_id: Mapped[int] = mapped_column(ForeignKey("newbies.id"), index=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("mentors.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default=RequestStatus.pending.value, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    newbie: Mapped[Newbie] = relationship(back_populates="requests")
    mentor: Mapped[Mentor] = relationship(back_populates="requests")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("mentor_sessions.id"), index=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, index=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=ReportStatus.open.value, index=True)
    resolved_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[MentorSession] = relationship(back_populates="reports")


class ChannelLog(Base):
    __tablename__ = "channel_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("mentor_sessions.id"), nullable=True, index=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, index=True)
    author_id: Mapped[int] = mapped_column(BigInteger, index=True)
    content: Mapped[str] = mapped_column(Text, default="")
    attachments: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BotSetting(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    mentor_session_days: Mapped[int] = mapped_column(Integer, default=14)
    security_reminder_days: Mapped[int] = mapped_column(Integer, default=3)
    session_category_name: Mapped[str] = mapped_column(String(128), default="Менторство")
    archive_category_name: Mapped[str] = mapped_column(String(128), default="Архив менторства")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
