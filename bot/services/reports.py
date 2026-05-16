from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Report


async def create_report(session: AsyncSession, session_id: int, reporter_id: int, reason: str) -> Report:
    report = Report(session_id=session_id, reporter_id=reporter_id, reason=reason.strip())
    session.add(report)
    await session.flush()
    return report
