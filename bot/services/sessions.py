from __future__ import annotations

from datetime import timedelta

import discord
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.database.models import (
    Mentor,
    MentorSession,
    MentorStatus,
    Newbie,
    Report,
    ReportStatus,
    SessionStatus,
    utcnow,
)
from bot.plugins.base import GamePlugin
from bot.ui.embeds import session_intro_embed
from bot.utils.helpers import slugify_channel_part


async def create_mentorship_session(
    db: AsyncSession,
    guild: discord.Guild,
    mentor_member: discord.Member,
    newbie_member: discord.Member,
    mentor: Mentor,
    newbie: Newbie,
    plugin: GamePlugin,
    settings: Settings,
    async_session_factory=None,
) -> MentorSession:
    category = await _get_or_create_category(guild, settings.session_category_name)
    moderator_role = discord.utils.get(guild.roles, name=settings.moderator_role_name)
    overwrites: dict[discord.Role | discord.Member, discord.PermissionOverwrite] = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        mentor_member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        newbie_member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    if moderator_role:
        overwrites[moderator_role] = discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True)

    channel_name = f"mentor-{slugify_channel_part(mentor.game_nick)}-{slugify_channel_part(newbie.game_nick)}"
    channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites, category=category)

    now = utcnow()
    mentor_session = MentorSession(
        mentor_id=mentor.id,
        newbie_id=newbie.id,
        channel_id=channel.id,
        expires_at=now + timedelta(days=settings.mentor_session_days or plugin.default_session_days),
    )
    db.add(mentor_session)
    newbie.status = "in_session"
    await db.flush()

    view = None
    if async_session_factory is not None:
        from bot.ui.views import SessionActionsView

        view = SessionActionsView(mentor_session.id, async_session_factory, settings, plugin)

    message = await channel.send(
        embed=session_intro_embed(mentor, newbie, plugin),
        view=view,
    )
    await message.pin(reason="Mentorship session rules")
    return mentor_session


async def finish_mentorship_session(
    db: AsyncSession,
    mentor_session: MentorSession,
    status: str = SessionStatus.completed.value,
    plugin: GamePlugin | None = None,
) -> None:
    mentor_session.status = status
    mentor_session.ended_at = utcnow()
    mentor_session.mentor.total_sessions += 1
    mentor_session.newbie.status = "completed"
    await db.flush()
    if plugin:
        await maybe_promote_probation_mentor(db, mentor_session.mentor, plugin)


async def maybe_promote_probation_mentor(
    db: AsyncSession,
    mentor: Mentor,
    plugin: GamePlugin,
) -> bool:
    if mentor.status != MentorStatus.probation.value:
        return False
    required_sessions = max(1, plugin.quarantine_sessions)
    if mentor.total_sessions < required_sessions:
        return False
    open_reports = (
        await db.execute(
            select(func.count(Report.id))
            .join(MentorSession, Report.session_id == MentorSession.id)
            .where(MentorSession.mentor_id == mentor.id, Report.status == ReportStatus.open.value)
        )
    ).scalar_one()
    if open_reports:
        return False
    mentor.status = MentorStatus.approved.value
    await db.flush()
    return True


async def archive_channel(guild: discord.Guild, channel_id: int, settings: Settings) -> None:
    channel = guild.get_channel(channel_id)
    if not isinstance(channel, discord.TextChannel):
        return
    archive_category = await _get_or_create_category(guild, settings.archive_category_name)
    await channel.edit(category=archive_category, reason="Mentorship completed")


async def _get_or_create_category(guild: discord.Guild, name: str) -> discord.CategoryChannel:
    category = discord.utils.get(guild.categories, name=name)
    if category:
        return category
    return await guild.create_category(name=name)
