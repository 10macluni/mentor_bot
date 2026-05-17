from __future__ import annotations

from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.config import Settings
from bot.database.models import MentorSession, Report, ReportStatus, SessionStatus, utcnow
from bot.plugins.base import GamePlugin
from bot.services.reports import apply_low_staff_report_sanction, create_report
from bot.services.sessions import archive_channel, finish_mentorship_session


class SessionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        self.bot = bot
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings

    @app_commands.command(name="finish_session", description="Завершить активное менторство")
    async def finish_session(self, interaction: discord.Interaction, session_id: int) -> None:
        await interaction.response.defer(ephemeral=True)
        async with self.async_session_factory() as db:
            result = await db.execute(
                select(MentorSession)
                .options(selectinload(MentorSession.mentor), selectinload(MentorSession.newbie))
                .where(MentorSession.id == session_id)
            )
            mentor_session = result.scalar_one_or_none()
            if not mentor_session or mentor_session.status != SessionStatus.active.value:
                await interaction.followup.send("Активная сессия не найдена.", ephemeral=True)
                return
            allowed = {mentor_session.mentor.discord_id, mentor_session.newbie.discord_id}
            if interaction.user.id not in allowed:
                await interaction.followup.send("Завершить сессию может только участник или администратор.", ephemeral=True)
                return
            await finish_mentorship_session(db, mentor_session, settings=self.settings, plugin=self.plugin)
            await db.commit()
        if interaction.guild and mentor_session.channel_id:
            await archive_channel(interaction.guild, mentor_session.channel_id, self.settings)
        await interaction.followup.send("Сессия завершена. Оба участника могут оставить отзыв через /review.", ephemeral=True)

    @app_commands.command(name="extend_session", description="Продлить менторство")
    async def extend_session(self, interaction: discord.Interaction, session_id: int, days: int = 7) -> None:
        if days < 1 or days > 14:
            await interaction.response.send_message("Продление должно быть от 1 до 14 дней.", ephemeral=True)
            return
        async with self.async_session_factory() as db:
            result = await db.execute(
                select(MentorSession)
                .options(selectinload(MentorSession.mentor), selectinload(MentorSession.newbie))
                .where(MentorSession.id == session_id)
            )
            mentor_session = result.scalar_one_or_none()
            if not mentor_session or mentor_session.status != SessionStatus.active.value:
                await interaction.response.send_message("Активная сессия не найдена.", ephemeral=True)
                return
            if interaction.user.id not in {mentor_session.mentor.discord_id, mentor_session.newbie.discord_id}:
                await interaction.response.send_message("Продлить сессию может только участник.", ephemeral=True)
                return
            mentor_session.expires_at = mentor_session.expires_at + timedelta(days=days)
            mentor_session.extended = True
            await db.commit()
        await interaction.response.send_message("Сессия продлена.", ephemeral=True)

    @app_commands.command(name="report", description="Пожаловаться на проблему в сессии")
    async def report(self, interaction: discord.Interaction, session_id: int, reason: str) -> None:
        async with self.async_session_factory() as db:
            report = await create_report(db, session_id, interaction.user.id, reason)
            await db.commit()
        await interaction.response.send_message(f"Жалоба #{report.id} создана и передана модераторам.", ephemeral=True)

    @app_commands.command(name="resolve_report", description="Закрыть жалобу")
    async def resolve_report(self, interaction: discord.Interaction, report_id: int, resolved: bool = True) -> None:
        async with self.async_session_factory() as db:
            report = (await db.execute(select(Report).where(Report.id == report_id))).scalar_one_or_none()
            if not report:
                await interaction.response.send_message("Жалоба не найдена.", ephemeral=True)
                return
            report.status = ReportStatus.resolved.value if resolved else ReportStatus.dismissed.value
            report.resolved_by = interaction.user.id
            report.resolved_at = utcnow()
            sanction = await apply_low_staff_report_sanction(db, report, self.settings)
            await db.commit()
        message = "Жалоба закрыта."
        if sanction:
            message = f"Жалоба закрыта, авто-санкция применена: {sanction}."
        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
    await bot.add_cog(SessionsCog(bot, async_session_factory, plugin, settings))
