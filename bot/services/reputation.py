from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Mentor, Review


def calculate_mentor_badges(total_sessions: int, rating: float) -> list[str]:
    badges: list[str] = []
    if total_sessions >= 5:
        badges.append("🥉 Бронзовый ментор")
    if total_sessions >= 15:
        badges.append("🥈 Серебряный ментор")
    if total_sessions >= 30:
        badges.append("🥇 Золотой ментор")
    if total_sessions >= 50 and rating >= 4.5:
        badges.append("💎 Легендарный ментор")
    return badges


def validate_rating(rating: int) -> int:
    if rating < 1 or rating > 5:
        raise ValueError("Rating must be between 1 and 5")
    return rating


async def recalculate_mentor_rating(session: AsyncSession, mentor: Mentor) -> None:
    result = await session.execute(select(func.avg(Review.rating)).where(Review.target_id == mentor.discord_id))
    average = result.scalar()
    mentor.rating = round(float(average or 0.0), 2)
