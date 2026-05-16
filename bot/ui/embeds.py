from __future__ import annotations

import discord

from bot.database.models import Mentor, MentorSession, Newbie
from bot.plugins.base import GamePlugin
from bot.services.reputation import calculate_mentor_badges


def mentor_profile_embed(mentor: Mentor, plugin: GamePlugin) -> discord.Embed:
    embed = discord.Embed(title=f"Профиль ментора: {mentor.game_nick}", color=discord.Color.green())
    embed.add_field(name="Игра", value=plugin.name, inline=True)
    embed.add_field(name="Статус", value=mentor.status, inline=True)
    embed.add_field(name="Языки", value=", ".join(mentor.languages) or "—", inline=True)
    embed.add_field(name="Часовой пояс", value=mentor.timezone, inline=True)
    embed.add_field(name="Специализации", value=plugin.format_specializations(mentor.specializations), inline=False)
    embed.add_field(name="Опыт", value=mentor.experience or "—", inline=False)
    embed.add_field(name="Рейтинг", value=f"{mentor.rating:.2f}/5", inline=True)
    embed.add_field(name="Завершено", value=str(mentor.total_sessions), inline=True)
    badges = calculate_mentor_badges(mentor.total_sessions, mentor.rating)
    embed.add_field(name="Бейджи", value="\n".join(badges) if badges else "—", inline=False)
    return embed


def newbie_profile_embed(newbie: Newbie, plugin: GamePlugin) -> discord.Embed:
    embed = discord.Embed(title=f"Анкета новичка: {newbie.game_nick}", color=discord.Color.blurple())
    embed.add_field(name="Игра", value=plugin.name, inline=True)
    embed.add_field(name="Статус", value=newbie.status, inline=True)
    embed.add_field(name="Язык", value=newbie.language, inline=True)
    embed.add_field(name="Часовой пояс", value=newbie.timezone, inline=True)
    embed.add_field(name="Нужна помощь", value=plugin.format_specializations(newbie.needs), inline=False)
    embed.add_field(name="Комментарий", value=newbie.comment or "—", inline=False)
    return embed


def mentor_candidate_embed(mentor: Mentor, matched_specializations: tuple[str, ...], plugin: GamePlugin) -> discord.Embed:
    embed = mentor_profile_embed(mentor, plugin)
    embed.title = f"Подходящий ментор: {mentor.game_nick}"
    embed.add_field(name="Совпадения", value=plugin.format_specializations(matched_specializations), inline=False)
    return embed


def session_intro_embed(mentor: Mentor, newbie: Newbie, plugin: GamePlugin) -> discord.Embed:
    rules = "\n".join(f"• {rule}" for rule in plugin.safety_rules)
    embed = discord.Embed(title="Сессия менторства создана", color=discord.Color.gold())
    embed.add_field(name="Ментор", value=f"{mentor.game_nick} (<@{mentor.discord_id}>)", inline=False)
    embed.add_field(name="Новичок", value=f"{newbie.game_nick} (<@{newbie.discord_id}>)", inline=False)
    embed.add_field(name="Правила безопасности", value=rules, inline=False)
    embed.set_footer(text="Используйте кнопки завершения и жалобы или slash-команды бота.")
    return embed


def session_summary_embed(mentor_session: MentorSession) -> discord.Embed:
    embed = discord.Embed(title=f"Сессия #{mentor_session.id}", color=discord.Color.dark_teal())
    embed.add_field(name="Ментор", value=mentor_session.mentor.game_nick, inline=True)
    embed.add_field(name="Новичок", value=mentor_session.newbie.game_nick, inline=True)
    embed.add_field(name="Статус", value=mentor_session.status, inline=True)
    embed.add_field(name="Окончание", value=mentor_session.expires_at.isoformat(), inline=False)
    return embed
