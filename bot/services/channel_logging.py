from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import ChannelLog, MentorSession, SessionStatus


async def log_channel_message(
    session: AsyncSession,
    channel_id: int,
    author_id: int,
    content: str,
    attachments: list[str],
) -> ChannelLog:
    mentor_session_id: int | None = None
    result = await session.execute(
        select(MentorSession.id).where(
            MentorSession.channel_id == channel_id,
            MentorSession.status == SessionStatus.active.value,
        )
    )
    row = result.first()
    if row:
        mentor_session_id = row[0]

    log = ChannelLog(
        session_id=mentor_session_id,
        channel_id=channel_id,
        author_id=author_id,
        content=content,
        attachments=attachments,
    )
    session.add(log)
    await session.flush()
    return log
