from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from bot.config import Settings
from bot.database.models import BotSetting, ChannelLog, Mentor, MentorSession, MentorStatus, Newbie, SessionStatus
from bot.plugins.base import GamePlugin
from bot.ui.embeds import session_summary_embed
from bot.utils.checks import admin_check, moderator_check


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        self.bot = bot
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings

    @app_commands.command(name="admin_approve", description="Одобрить заявку ментора")
    @admin_check(Settings.from_env())
    async def admin_approve(self, interaction: discord.Interaction, user: discord.Member) -> None:
        async with self.async_session_factory() as db:
            mentor = (await db.execute(select(Mentor).where(Mentor.discord_id == user.id))).scalar_one_or_none()
            if not mentor:
                await interaction.response.send_message("Заявка ментора не найдена.", ephemeral=True)
                return
            mentor.status = MentorStatus.approved.value
            await db.commit()
        role = discord.utils.get(interaction.guild.roles, name=self.settings.mentor_role_name) if interaction.guild else None
        if role:
            await user.add_roles(role, reason="Mentor approved")
        await user.send("Ваша заявка ментора одобрена.")
        await interaction.response.send_message("Ментор одобрен.", ephemeral=True)

    @app_commands.command(name="admin_reject", description="Отклонить заявку ментора")
    @admin_check(Settings.from_env())
    async def admin_reject(self, interaction: discord.Interaction, user: discord.Member, reason: str = "") -> None:
        async with self.async_session_factory() as db:
            mentor = (await db.execute(select(Mentor).where(Mentor.discord_id == user.id))).scalar_one_or_none()
            if mentor:
                mentor.status = MentorStatus.rejected.value
                await db.commit()
        await user.send(f"Ваша заявка ментора отклонена. Причина: {reason or 'не указана'}")
        await interaction.response.send_message("Заявка отклонена.", ephemeral=True)

    @app_commands.command(name="admin_ban", description="Заблокировать пользователя в системе")
    @admin_check(Settings.from_env())
    async def admin_ban(self, interaction: discord.Interaction, user: discord.Member, reason: str = "") -> None:
        async with self.async_session_factory() as db:
            mentor = (await db.execute(select(Mentor).where(Mentor.discord_id == user.id))).scalar_one_or_none()
            newbie = (await db.execute(select(Newbie).where(Newbie.discord_id == user.id))).scalar_one_or_none()
            if mentor:
                mentor.status = MentorStatus.banned.value
            if newbie:
                newbie.status = "banned"
            await db.commit()
        role = discord.utils.get(interaction.guild.roles, name=self.settings.mentor_role_name) if interaction.guild else None
        if role:
            await user.remove_roles(role, reason=reason or "Banned in mentorship system")
        await interaction.response.send_message("Пользователь заблокирован в системе.", ephemeral=True)

    @app_commands.command(name="admin_unban", description="Разблокировать пользователя")
    @admin_check(Settings.from_env())
    async def admin_unban(self, interaction: discord.Interaction, user: discord.Member) -> None:
        async with self.async_session_factory() as db:
            mentor = (await db.execute(select(Mentor).where(Mentor.discord_id == user.id))).scalar_one_or_none()
            newbie = (await db.execute(select(Newbie).where(Newbie.discord_id == user.id))).scalar_one_or_none()
            if mentor and mentor.status == MentorStatus.banned.value:
                mentor.status = MentorStatus.probation.value if self.settings.low_staff_enabled else MentorStatus.pending.value
            if newbie and newbie.status == "banned":
                newbie.status = "searching"
            await db.commit()
        await interaction.response.send_message("Пользователь разблокирован.", ephemeral=True)

    @app_commands.command(name="admin_stats", description="Статистика системы менторства")
    @admin_check(Settings.from_env())
    async def admin_stats(self, interaction: discord.Interaction) -> None:
        async with self.async_session_factory() as db:
            mentors = (await db.execute(select(func.count(Mentor.id)))).scalar_one()
            approved = (await db.execute(select(func.count(Mentor.id)).where(Mentor.status == MentorStatus.approved.value))).scalar_one()
            probation = (await db.execute(select(func.count(Mentor.id)).where(Mentor.status == MentorStatus.probation.value))).scalar_one()
            active = (await db.execute(select(func.count(MentorSession.id)).where(MentorSession.status == SessionStatus.active.value))).scalar_one()
            completed = (await db.execute(select(func.count(MentorSession.id)).where(MentorSession.status == SessionStatus.completed.value))).scalar_one()
            avg_rating = (await db.execute(select(func.avg(Mentor.rating)).where(Mentor.rating > 0))).scalar() or 0
        embed = discord.Embed(title="Статистика менторства", color=discord.Color.blue())
        embed.add_field(name="Менторы", value=f"{approved} approved, {probation} probation из {mentors}", inline=True)
        embed.add_field(name="Активные сессии", value=str(active), inline=True)
        embed.add_field(name="Завершённые", value=str(completed), inline=True)
        embed.add_field(name="Средний рейтинг", value=f"{float(avg_rating):.2f}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="admin_settings", description="Посмотреть или изменить настройки бота")
    @admin_check(Settings.from_env())
    async def admin_settings(
        self,
        interaction: discord.Interaction,
        mentor_session_days: int | None = None,
        security_reminder_days: int | None = None,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Команда доступна только на сервере.", ephemeral=True)
            return
        async with self.async_session_factory() as db:
            setting = (await db.execute(select(BotSetting).where(BotSetting.guild_id == interaction.guild.id))).scalar_one_or_none()
            if not setting:
                setting = BotSetting(
                    guild_id=interaction.guild.id,
                    mentor_session_days=self.settings.mentor_session_days,
                    security_reminder_days=self.settings.security_reminder_days,
                    session_category_name=self.settings.session_category_name,
                    archive_category_name=self.settings.archive_category_name,
                )
                db.add(setting)
            if mentor_session_days is not None:
                setting.mentor_session_days = max(1, min(90, mentor_session_days))
            if security_reminder_days is not None:
                setting.security_reminder_days = max(1, min(30, security_reminder_days))
            await db.commit()
        await interaction.response.send_message(
            f"Настройки: срок={setting.mentor_session_days} дней, напоминания={setting.security_reminder_days} дней.",
            ephemeral=True,
        )

    @app_commands.command(name="admin_sessions", description="Список активных сессий")
    @moderator_check(Settings.from_env())
    async def admin_sessions(self, interaction: discord.Interaction) -> None:
        async with self.async_session_factory() as db:
            sessions = (
                await db.execute(
                    select(MentorSession)
                    .options(selectinload(MentorSession.mentor), selectinload(MentorSession.newbie))
                    .where(MentorSession.status == SessionStatus.active.value)
                    .limit(10)
                )
            ).scalars().all()
        if not sessions:
            await interaction.response.send_message("Активных сессий нет.", ephemeral=True)
            return
        await interaction.response.send_message(embeds=[session_summary_embed(item) for item in sessions], ephemeral=True)

    @app_commands.command(name="admin_logs", description="История сообщений пользователя")
    @moderator_check(Settings.from_env())
    async def admin_logs(self, interaction: discord.Interaction, user: discord.User) -> None:
        async with self.async_session_factory() as db:
            logs = (
                await db.execute(select(ChannelLog).where(ChannelLog.author_id == user.id).order_by(ChannelLog.created_at.desc()).limit(10))
            ).scalars().all()
        if not logs:
            await interaction.response.send_message("Логи не найдены.", ephemeral=True)
            return
        text = "\n".join(f"#{log.channel_id}: {log.content[:120]}" for log in logs)
        await interaction.response.send_message(text, ephemeral=True)


async def setup(bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
    await bot.add_cog(AdminCog(bot, async_session_factory, plugin, settings))
