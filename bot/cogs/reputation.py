from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select

from bot.config import Settings
from bot.database.models import Mentor
from bot.plugins.base import GamePlugin
from bot.ui.modals import ReviewModal


class ReputationCog(commands.Cog):
    def __init__(self, bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        self.bot = bot
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings

    @app_commands.command(name="review", description="Оставить отзыв после менторства")
    async def review(self, interaction: discord.Interaction, target: discord.User) -> None:
        await interaction.response.send_modal(ReviewModal(self.async_session_factory, target.id))

    @app_commands.command(name="leaderboard", description="Топ-10 менторов")
    @app_commands.describe(mode="rating или sessions")
    async def leaderboard(self, interaction: discord.Interaction, mode: str = "rating") -> None:
        order_by = Mentor.total_sessions.desc() if mode == "sessions" else Mentor.rating.desc()
        async with self.async_session_factory() as db:
            mentors = (
                await db.execute(
                    select(Mentor).where(Mentor.status == "approved", Mentor.game_key == self.plugin.key).order_by(order_by).limit(10)
                )
            ).scalars().all()
        if not mentors:
            await interaction.response.send_message("Пока нет менторов для лидерборда.", ephemeral=True)
            return
        lines = [
            f"{index}. {mentor.game_nick} — рейтинг {mentor.rating:.2f}, сессий {mentor.total_sessions}"
            for index, mentor in enumerate(mentors, start=1)
        ]
        await interaction.response.send_message("\n".join(lines), ephemeral=True)


async def setup(bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
    await bot.add_cog(ReputationCog(bot, async_session_factory, plugin, settings))
