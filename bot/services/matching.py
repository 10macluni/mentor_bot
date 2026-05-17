from __future__ import annotations

import re
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Mentor, MentorSession, MentorStatus, Newbie, SessionStatus

PROBATION_MAX_NEWBIES = 1


class MentorLike(Protocol):
    id: int
    discord_id: int
    game_key: str
    game_nick: str
    timezone: str
    languages: list[str]
    specializations: list[str]
    max_newbies: int
    status: str
    rating: float
    total_sessions: int


class NewbieLike(Protocol):
    game_key: str
    timezone: str
    language: str
    needs: list[str]


@dataclass(frozen=True)
class MentorCandidate:
    mentor: MentorLike
    matched_specializations: tuple[str, ...]
    active_sessions: int
    timezone_delta: int
    score: float


def parse_utc_offset(value: str) -> int:
    match = re.fullmatch(r"UTC(?:([+-])(\d{1,2}))?", value.strip().upper())
    if not match:
        raise ValueError(f"Invalid timezone '{value}', expected UTC, UTC+3 or UTC-5")
    sign, hours = match.groups()
    offset = int(hours or 0)
    if offset > 14:
        raise ValueError("UTC offset must be <= 14")
    return -offset if sign == "-" else offset


def timezone_delta(left: str, right: str) -> int:
    return abs(parse_utc_offset(left) - parse_utc_offset(right))


def find_matching_mentors(
    newbie: NewbieLike,
    mentors: Sequence[MentorLike],
    active_session_counts: dict[int, int] | None = None,
    max_results: int = 5,
    eligible_statuses: Collection[str] = (MentorStatus.approved.value, MentorStatus.probation.value),
    probation_max_newbies: int = 1,
) -> list[MentorCandidate]:
    counts = active_session_counts or {}
    eligible_status_set = set(eligible_statuses)
    candidates: list[MentorCandidate] = []
    newbie_needs = set(newbie.needs)
    newbie_language = newbie.language.lower()

    for mentor in mentors:
        if mentor.game_key != newbie.game_key or mentor.status not in eligible_status_set:
            continue
        if newbie_language not in {language.lower() for language in mentor.languages}:
            continue
        delta = timezone_delta(newbie.timezone, mentor.timezone)
        if delta > 3:
            continue
        overlap = tuple(sorted(newbie_needs.intersection(mentor.specializations)))
        if not overlap:
            continue
        active_count = counts.get(mentor.id, 0)
        capacity = mentor.max_newbies
        probation_penalty = 0
        if mentor.status == MentorStatus.probation.value:
            capacity = min(capacity, probation_max_newbies)
            probation_penalty = 25
        if active_count >= capacity:
            continue
        score = (
            (mentor.rating * 100)
            + (mentor.total_sessions * 2)
            + (len(overlap) * 10)
            - delta
            - probation_penalty
        )
        candidates.append(
            MentorCandidate(
                mentor=mentor,
                matched_specializations=overlap,
                active_sessions=active_count,
                timezone_delta=delta,
                score=score,
            )
        )

    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.mentor.rating,
            candidate.score,
            candidate.mentor.total_sessions,
        ),
        reverse=True,
    )[:max_results]


async def active_session_counts(session: AsyncSession) -> dict[int, int]:
    rows = await session.execute(
        select(MentorSession.mentor_id, func.count(MentorSession.id))
        .where(MentorSession.status == SessionStatus.active.value)
        .group_by(MentorSession.mentor_id)
    )
    return {mentor_id: count for mentor_id, count in rows.all()}


def matchable_mentor_statuses() -> tuple[str, ...]:
    return (MentorStatus.approved.value, MentorStatus.probation.value)


async def find_matches_for_newbie(
    session: AsyncSession,
    newbie: Newbie,
    max_results: int = 5,
) -> list[MentorCandidate]:
    mentors = (
        await session.execute(select(Mentor).where(Mentor.game_key == newbie.game_key))
    ).scalars().all()
    counts = await active_session_counts(session)
    return find_matching_mentors(
        newbie,
        mentors,
        counts,
        max_results=max_results,
        eligible_statuses=matchable_mentor_statuses(),
        probation_max_newbies=PROBATION_MAX_NEWBIES,
    )
