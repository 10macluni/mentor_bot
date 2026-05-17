from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Mentor, MentorSession, MentorStatus, Report, ReportStatus


async def create_report(session: AsyncSession, session_id: int, reporter_id: int, reason: str) -> Report:
    report = Report(session_id=session_id, reporter_id=reporter_id, reason=reason.strip())
    session.add(report)
    await session.flush()
    return report


async def apply_low_staff_report_sanction(session: AsyncSession, report: Report) -> str | None:
    if report.status != ReportStatus.resolved.value:
        return None
    mentor = (
        await session.execute(
            select(Mentor)
            .join(MentorSession, MentorSession.mentor_id == Mentor.id)
            .where(MentorSession.id == report.session_id)
        )
    ).scalar_one_or_none()
    if mentor is None or mentor.status == MentorStatus.banned.value:
        return None
    resolved_reports = (
        await session.execute(
            select(func.count(Report.id))
            .join(MentorSession, Report.session_id == MentorSession.id)
            .where(MentorSession.mentor_id == mentor.id, Report.status == ReportStatus.resolved.value)
        )
    ).scalar_one()
    if resolved_reports >= 3:
        mentor.status = MentorStatus.banned.value
        return MentorStatus.banned.value
    if mentor.status == MentorStatus.approved.value:
        mentor.status = MentorStatus.probation.value
        return MentorStatus.probation.value
    return None
