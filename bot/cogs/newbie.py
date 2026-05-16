from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import Settings
from bot.plugins.base import GamePlugin
from bot.ui.modals import NewbieFindMentorModal


class NewbieCog(commands.Cog):
    def __init__(self, bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
        self.bot = bot
        self.async_session_factory = async_session_factory
        self.plugin = plugin
        self.settings = settings

    @app_commands.command(name="find_mentor", description="Заполнить анкету новичка и найти ментора")
    async def find_mentor(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(NewbieFindMentorModal(self.async_session_factory, self.plugin, self.settings))


async def setup(bot: commands.Bot, async_session_factory, plugin: GamePlugin, settings: Settings) -> None:
    await bot.add_cog(NewbieCog(bot, async_session_factory, plugin, settings))
