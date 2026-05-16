from __future__ import annotations

import re


def parse_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def slugify_channel_part(value: str, fallback: str = "user") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9а-яА-Я_-]+", "-", value.strip()).strip("-").lower()
    return cleaned[:40] or fallback


def parse_schedule(value: str) -> dict[str, str]:
    if not value.strip():
        return {}
    schedule: dict[str, str] = {}
    for part in value.split(";"):
        if ":" not in part:
            continue
        day, time_range = part.split(":", 1)
        schedule[day.strip().lower()] = time_range.strip()
    return schedule


def parse_key_value_details(value: str) -> dict[str, str]:
    details: dict[str, str] = {}
    for part in value.split(";"):
        if "=" not in part:
            details.setdefault("experience", part.strip())
            continue
        key, raw_value = part.split("=", 1)
        details[key.strip().lower()] = raw_value.strip()
    return details
