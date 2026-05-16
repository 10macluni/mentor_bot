from __future__ import annotations

import discord
from discord import app_commands

from bot.config import Settings


def has_named_role(member: discord.Member, role_name: str) -> bool:
    return any(role.name == role_name for role in member.roles)


def admin_check(settings: Settings) -> app_commands.Check:
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        return has_named_role(interaction.user, settings.admin_role_name) or interaction.user.guild_permissions.manage_guild

    return app_commands.check(predicate)


def moderator_check(settings: Settings) -> app_commands.Check:
    async def predicate(interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        return (
            has_named_role(interaction.user, settings.moderator_role_name)
            or has_named_role(interaction.user, settings.admin_role_name)
            or interaction.user.guild_permissions.manage_messages
        )

    return app_commands.check(predicate)
