from __future__ import annotations

import logging
from datetime import timedelta

import discord
from discord.ext import commands, tasks
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.config import Settings
from bot.database.models import MentorSession, SessionStatus, utcnow
from bot.plugins.base import GamePlugin

logger = logging.getLogger(__name__)


class NotificationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        self.bot = bot
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings
        self.security_reminders.change_interval(hours=settings.security_reminder_days * 24)
        self.session_deadline_notifications.start()
        self.security_reminders.start()

    def cog_unload(self) -> None:
        self.session_deadline_notifications.cancel()
        self.security_reminders.cancel()

    @tasks.loop(hours=12)
    async def session_deadline_notifications(self) -> None:
        now = utcnow()
        threshold = now + timedelta(days=2)
        async with self.async_session_factory() as db:
            sessions = (
                await db.execute(
                    select(MentorSession)
                    .options(selectinload(MentorSession.mentor), selectinload(MentorSession.newbie))
                    .where(MentorSession.status == SessionStatus.active.value, MentorSession.expires_at <= threshold)
                )
            ).scalars().all()
        for mentor_session in sessions:
            await self._send_to_channel(mentor_session.channel_id, "Сессия менторства скоро закончится. Используйте /extend_session или /finish_session.")

    @session_deadline_notifications.before_loop
    async def before_deadline_loop(self) -> None:
        await self.bot.wait_until_ready()

    @tasks.loop(hours=72)
    async def security_reminders(self) -> None:
        rules = "\n".join(f"• {rule}" for rule in self.plugin.safety_rules)
        async with self.async_session_factory() as db:
            sessions = (
                await db.execute(select(MentorSession).where(MentorSession.status == SessionStatus.active.value))
            ).scalars().all()
        for mentor_session in sessions:
            await self._send_to_channel(mentor_session.channel_id, f"⚠️ Напоминание безопасности:\n{rules}")

    @security_reminders.before_loop
    async def before_security_loop(self) -> None:
        await self.bot.wait_until_ready()

    async def _send_to_channel(self, channel_id: int | None, message: str) -> None:
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(message)
            except discord.HTTPException:
                logger.exception("Failed to send notification to channel %s", channel_id)


async def setup(bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
    await bot.add_cog(NotificationsCog(bot, async_session_factory, plugin, settings))
