from __future__ import annotations

import discord
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.config import Settings
from bot.database.models import Mentor, MentorRequest, MentorSession, Newbie, RequestStatus, SessionStatus
from bot.plugins.base import GamePlugin
from bot.services.reports import create_report
from bot.services.sessions import archive_channel, create_mentorship_session, finish_mentorship_session
from bot.ui.embeds import newbie_profile_embed


class MentorMatchesView(discord.ui.View):
    def __init__(self, candidates, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        super().__init__(timeout=900)
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings
        for index, candidate in enumerate(candidates, start=1):
            button = discord.ui.Button(
                label=f"📩 Запрос #{index}: {candidate.mentor.game_nick}",
                style=discord.ButtonStyle.primary,
                custom_id=f"mentor_request:{candidate.mentor.id}",
            )
            button.callback = self._request_callback(candidate.mentor.id)
            self.add_item(button)

    def _request_callback(self, mentor_id: int):
        async def callback(interaction: discord.Interaction) -> None:
            await interaction.response.defer(ephemeral=True)
            async with self.async_session_factory() as db:
                newbie = (
                    await db.execute(select(Newbie).where(Newbie.discord_id == interaction.user.id, Newbie.game_key == self.plugin.key))
                ).scalar_one_or_none()
                mentor = (await db.execute(select(Mentor).where(Mentor.id == mentor_id))).scalar_one_or_none()
                if not newbie or not mentor:
                    await interaction.followup.send("Анкета не найдена. Заполните /find_mentor ещё раз.", ephemeral=True)
                    return
                request = MentorRequest(newbie_id=newbie.id, mentor_id=mentor.id)
                db.add(request)
                await db.commit()

            mentor_user = interaction.client.get_user(mentor.discord_id) or await interaction.client.fetch_user(mentor.discord_id)
            await mentor_user.send(
                "Новый запрос на менторство.",
                embed=newbie_profile_embed(newbie, self.plugin),
                view=MentorRequestResponseView(request.id, self.async_session_factory, self.plugin, self.settings),
            )
            await interaction.followup.send("Запрос отправлен ментору в ЛС.", ephemeral=True)

        return callback


class MentorRequestResponseView(discord.ui.View):
    def __init__(self, request_id: int, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        super().__init__(timeout=settings.request_timeout_hours * 3600)
        self.request_id = request_id
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings

    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        guild = interaction.guild
        if guild is None and self.settings.guild_id:
            guild = interaction.client.get_guild(self.settings.guild_id)
        if guild is None:
            await interaction.response.send_message("Укажите DISCORD_GUILD_ID, чтобы принимать запросы из ЛС.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        async with self.async_session_factory() as db:
            result = await db.execute(
                select(MentorRequest)
                .options(selectinload(MentorRequest.mentor), selectinload(MentorRequest.newbie))
                .where(MentorRequest.id == self.request_id)
            )
            request = result.scalar_one_or_none()
            if not request or request.status != RequestStatus.pending.value:
                await interaction.followup.send("Запрос уже обработан или не найден.", ephemeral=True)
                return
            mentor_member = guild.get_member(request.mentor.discord_id) or await guild.fetch_member(request.mentor.discord_id)
            newbie_member = guild.get_member(request.newbie.discord_id) or await guild.fetch_member(request.newbie.discord_id)
            request.status = RequestStatus.accepted.value
            await create_mentorship_session(
                db,
                guild,
                mentor_member,
                newbie_member,
                request.mentor,
                request.newbie,
                self.plugin,
                self.settings,
                self.async_session_factory,
            )
            await db.commit()
        await interaction.followup.send("Запрос принят, приватный канал создан.", ephemeral=True)
        try:
            await newbie_member.send("Ментор принял запрос. Канал менторства создан на сервере.")
        except discord.HTTPException:
            pass

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        async with self.async_session_factory() as db:
            request = (await db.execute(select(MentorRequest).where(MentorRequest.id == self.request_id))).scalar_one_or_none()
            if request and request.status == RequestStatus.pending.value:
                request.status = RequestStatus.rejected.value
                await db.commit()
        await interaction.followup.send("Запрос отклонён.", ephemeral=True)


class SessionActionsView(discord.ui.View):
    def __init__(self, mentor_session_id: int, async_session_factory, settings: Settings) -> None:
        super().__init__(timeout=None)
        self.mentor_session_id = mentor_session_id
        self.async_session_factory = async_session_factory
        self.settings = settings

    @discord.ui.button(label="🏁 Завершить менторство", style=discord.ButtonStyle.secondary)
    async def finish(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        async with self.async_session_factory() as db:
            result = await db.execute(
                select(MentorSession)
                .options(selectinload(MentorSession.mentor), selectinload(MentorSession.newbie))
                .where(MentorSession.id == self.mentor_session_id)
            )
            mentor_session = result.scalar_one_or_none()
            if not mentor_session or mentor_session.status != SessionStatus.active.value:
                await interaction.followup.send("Активная сессия не найдена.", ephemeral=True)
                return
            if interaction.user.id not in {mentor_session.mentor.discord_id, mentor_session.newbie.discord_id}:
                await interaction.followup.send("Завершить сессию может только участник.", ephemeral=True)
                return
            await finish_mentorship_session(db, mentor_session)
            await db.commit()
        if interaction.guild and mentor_session.channel_id:
            await archive_channel(interaction.guild, mentor_session.channel_id, self.settings)
        await interaction.followup.send("Сессия завершена. Оставьте отзыв через /review.", ephemeral=True)

    @discord.ui.button(label="🚨 Пожаловаться", style=discord.ButtonStyle.danger)
    async def report(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        async with self.async_session_factory() as db:
            report = await create_report(db, self.mentor_session_id, interaction.user.id, "Жалоба создана кнопкой в канале")
            await db.commit()
        await interaction.response.send_message(
            f"Жалоба #{report.id} создана. Добавьте детали командой /report {self.mentor_session_id} <причина>.",
            ephemeral=True,
        )
