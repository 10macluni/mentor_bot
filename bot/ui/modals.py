from __future__ import annotations

import discord
from sqlalchemy import select

from bot.config import Settings
from bot.database.models import Mentor, Newbie, Review
from bot.plugins.base import GamePlugin
from bot.services.matching import find_matches_for_newbie
from bot.services.reputation import recalculate_mentor_rating, validate_rating
from bot.ui.embeds import mentor_candidate_embed
from bot.ui.views import MentorMatchesView
from bot.utils.helpers import parse_csv, parse_key_value_details, parse_schedule


class MentorRegistrationModal(discord.ui.Modal):
    def __init__(self, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        super().__init__(title="Регистрация ментора")
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings
        self.game_nick = discord.ui.TextInput(label=plugin.mentor_nick_label, max_length=64)
        self.timezone = discord.ui.TextInput(label="Часовой пояс, например UTC+3", max_length=10)
        self.languages = discord.ui.TextInput(label="Языки через запятую: RU, EN", max_length=128)
        self.specializations = discord.ui.TextInput(label="Специализации ключами через запятую", style=discord.TextStyle.paragraph)
        self.experience = discord.ui.TextInput(
            label="Опыт; max=1-5; schedule=пн 18-22",
            style=discord.TextStyle.paragraph,
            required=False,
        )
        for item in (self.game_nick, self.timezone, self.languages, self.specializations, self.experience):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            specs = self.plugin.validate_specializations(parse_csv(str(self.specializations.value)))
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        details = parse_key_value_details(str(self.experience.value))
        try:
            max_newbies = int(details.get("max", "1"))
        except ValueError:
            await interaction.response.send_message("max должен быть числом от 1 до 5.", ephemeral=True)
            return
        if max_newbies < 1 or max_newbies > 5:
            await interaction.response.send_message("max должен быть числом от 1 до 5.", ephemeral=True)
            return
        async with self.async_session_factory() as db:
            mentor = (await db.execute(select(Mentor).where(Mentor.discord_id == interaction.user.id, Mentor.game_key == self.plugin.key))).scalar_one_or_none()
            if not mentor:
                mentor = Mentor(discord_id=interaction.user.id, game_key=self.plugin.key)
                db.add(mentor)
            mentor.game_nick = str(self.game_nick.value).strip()
            mentor.timezone = str(self.timezone.value).strip().upper()
            mentor.languages = parse_csv(str(self.languages.value))
            mentor.specializations = specs
            mentor.experience = details.get("experience", str(self.experience.value).strip())
            mentor.max_newbies = max_newbies
            mentor.schedule = parse_schedule(details.get("schedule", ""))
            mentor.status = "pending"
            await db.commit()
        await interaction.response.send_message("Анкета ментора отправлена на рассмотрение администрации.", ephemeral=True)


class NewbieFindMentorModal(discord.ui.Modal):
    def __init__(self, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        super().__init__(title="Найти ментора")
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings
        self.game_nick = discord.ui.TextInput(label=plugin.newbie_nick_label, max_length=64)
        self.timezone = discord.ui.TextInput(label="Часовой пояс, например UTC+3", max_length=10)
        self.language = discord.ui.TextInput(label="Язык: RU / EN / другое", max_length=16)
        self.needs = discord.ui.TextInput(label="Что нужно ключами через запятую", style=discord.TextStyle.paragraph)
        self.comment = discord.ui.TextInput(label="Комментарий", style=discord.TextStyle.paragraph, required=False)
        for item in (self.game_nick, self.timezone, self.language, self.needs, self.comment):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            needs = self.plugin.validate_specializations(parse_csv(str(self.needs.value)))
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        async with self.async_session_factory() as db:
            newbie = (await db.execute(select(Newbie).where(Newbie.discord_id == interaction.user.id, Newbie.game_key == self.plugin.key))).scalar_one_or_none()
            if not newbie:
                newbie = Newbie(discord_id=interaction.user.id, game_key=self.plugin.key)
                db.add(newbie)
            newbie.game_nick = str(self.game_nick.value).strip()
            newbie.timezone = str(self.timezone.value).strip().upper()
            newbie.language = str(self.language.value).strip().lower()
            newbie.needs = needs
            newbie.comment = str(self.comment.value).strip()
            newbie.status = "searching"
            await db.flush()
            matches = await find_matches_for_newbie(db, newbie)
            await db.commit()
        if not matches:
            await interaction.response.send_message(
                "Подходящих менторов нет. Попробуйте расширить критерии или оставить заявку в очереди.",
                ephemeral=True,
            )
            return
        embeds = [mentor_candidate_embed(candidate.mentor, candidate.matched_specializations, self.plugin) for candidate in matches]
        await interaction.response.send_message(
            "Найдены подходящие менторы:",
            embeds=embeds,
            view=MentorMatchesView(matches, self.async_session_factory, self.plugin, self.settings),
            ephemeral=True,
        )


class ReviewModal(discord.ui.Modal):
    def __init__(self, async_session_factory, target_id: int) -> None:
        super().__init__(title="Оценить участника")
        self.async_session_factory = async_session_factory
        self.target_id = target_id
        self.session_id = discord.ui.TextInput(label="ID сессии", max_length=16)
        self.rating = discord.ui.TextInput(label="Рейтинг 1-5", max_length=1)
        self.tags = discord.ui.TextInput(label="Теги через запятую", required=False)
        self.text = discord.ui.TextInput(label="Отзыв", style=discord.TextStyle.paragraph, required=False)
        for item in (self.session_id, self.rating, self.tags, self.text):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            rating = validate_rating(int(str(self.rating.value)))
            session_id = int(str(self.session_id.value))
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        async with self.async_session_factory() as db:
            review = Review(
                session_id=session_id,
                author_id=interaction.user.id,
                target_id=self.target_id,
                rating=rating,
                tags=parse_csv(str(self.tags.value)),
                text=str(self.text.value).strip(),
            )
            db.add(review)
            mentor = (await db.execute(select(Mentor).where(Mentor.discord_id == self.target_id))).scalar_one_or_none()
            if mentor:
                await db.flush()
                await recalculate_mentor_rating(db, mentor)
            await db.commit()
        await interaction.response.send_message("Отзыв сохранён.", ephemeral=True)
