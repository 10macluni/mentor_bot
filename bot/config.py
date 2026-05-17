from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    discord_token: str
    database_url: str
    game_plugin: str
    guild_id: int | None
    mentor_role_name: str
    moderator_role_name: str
    admin_role_name: str
    archive_category_name: str
    session_category_name: str
    mentor_session_days: int
    security_reminder_days: int
    request_timeout_hours: int
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            discord_token=os.getenv("DISCORD_TOKEN", ""),
            database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/mentor_bot.db"),
            game_plugin=os.getenv("GAME_PLUGIN", "ark_se"),
            guild_id=_optional_int(os.getenv("DISCORD_GUILD_ID")),
            mentor_role_name=os.getenv("MENTOR_ROLE_NAME", "Ментор"),
            moderator_role_name=os.getenv("MODERATOR_ROLE_NAME", "Модератор"),
            admin_role_name=os.getenv("ADMIN_ROLE_NAME", "Администратор"),
            archive_category_name=os.getenv("ARCHIVE_CATEGORY_NAME", "Архив менторства"),
            session_category_name=os.getenv("SESSION_CATEGORY_NAME", "Менторство"),
            mentor_session_days=int(os.getenv("MENTOR_SESSION_DAYS", "14")),
            security_reminder_days=int(os.getenv("SECURITY_REMINDER_DAYS", "3")),
            request_timeout_hours=int(os.getenv("REQUEST_TIMEOUT_HOURS", "24")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    @property
    def sqlite_path(self) -> Path | None:
        prefix = "sqlite+aiosqlite:///"
        if self.database_url.startswith(prefix):
            return Path(self.database_url.removeprefix(prefix)).expanduser()
        return None


def _optional_int(value: str | None) -> int | None:
    if not value:
        return None
    return int(value)
