from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from bot.config import Settings
from bot.database.models import Mentor, Newbie
from bot.plugins.base import GamePlugin
from bot.ui.embeds import mentor_profile_embed, newbie_profile_embed
from bot.ui.modals import MentorRegistrationModal


class MentorCog(commands.Cog):
    def __init__(self, bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        self.bot = bot
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings

    @app_commands.command(name="mentor_register", description="Подать заявку на роль ментора")
    async def mentor_register(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(MentorRegistrationModal(self.async_session_factory, self.plugin, self.settings))

    @app_commands.command(name="profile", description="Показать профиль участника")
    @app_commands.describe(user="Пользователь Discord")
    async def profile(self, interaction: discord.Interaction, user: discord.User | None = None) -> None:
        target = user or interaction.user
        async with self.async_session_factory() as db:
            mentor = (
                await db.execute(select(Mentor).where(Mentor.discord_id == target.id, Mentor.game_key == self.plugin.key))
            ).scalar_one_or_none()
            if mentor:
                await interaction.response.send_message(embed=mentor_profile_embed(mentor, self.plugin), ephemeral=True)
                return
            newbie = (
                await db.execute(select(Newbie).where(Newbie.discord_id == target.id, Newbie.game_key == self.plugin.key))
            ).scalar_one_or_none()
            if newbie:
                await interaction.response.send_message(embed=newbie_profile_embed(newbie, self.plugin), ephemeral=True)
                return
        await interaction.response.send_message("Профиль не найден.", ephemeral=True)


async def setup(bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
    await bot.add_cog(MentorCog(bot, async_session_factory, plugin, settings))
