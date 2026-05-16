from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from bot.config import Settings
from bot.database.db import async_session, init_db
from bot.plugins import registry
from bot.services.channel_logging import log_channel_message
from bot.utils.logger import configure_logging

logger = logging.getLogger(__name__)


class MentorBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.plugin = registry.get(settings.game_plugin)

    async def setup_hook(self) -> None:
        await init_db()
        for module_name in (
            "bot.cogs.mentor",
            "bot.cogs.newbie",
            "bot.cogs.admin",
            "bot.cogs.sessions",
            "bot.cogs.reputation",
            "bot.cogs.notifications",
        ):
            module = __import__(module_name, fromlist=["setup"])
            await module.setup(self, async_session, self.plugin, self.settings)

        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("Slash commands synced for guild %s", self.settings.guild_id)
        else:
            await self.tree.sync()
            logger.info("Global slash commands synced")

    async def on_ready(self) -> None:
        logger.info("Logged in as %s with plugin %s", self.user, self.plugin.key)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.guild:
            async with async_session() as db:
                await log_channel_message(
                    db,
                    message.channel.id,
                    message.author.id,
                    message.content,
                    [attachment.url for attachment in message.attachments],
                )
                await db.commit()
        await self.process_commands(message)


def build_bot() -> MentorBot:
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    if not settings.discord_token:
        logger.warning("DISCORD_TOKEN is empty; set it in .env before running the bot")
    return MentorBot(settings)


async def main() -> None:
    bot = build_bot()
    async with bot:
        await bot.start(bot.settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
