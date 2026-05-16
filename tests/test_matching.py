from dataclasses import dataclass

import pytest

from bot.services.matching import find_matching_mentors, parse_utc_offset, timezone_delta


@dataclass
class MentorStub:
    id: int
    discord_id: int
    game_key: str
    game_nick: str
    timezone: str
    languages: list[str]
    specializations: list[str]
    max_newbies: int
    status: str
    rating: float
    total_sessions: int


@dataclass
class NewbieStub:
    game_key: str
    timezone: str
    language: str
    needs: list[str]


def test_matching_applies_language_timezone_specialization_capacity_and_rating() -> None:
    newbie = NewbieStub("ark_se", "UTC+3", "ru", ["pvp", "taming"])
    mentors = [
        MentorStub(1, 10, "ark_se", "Top", "UTC+1", ["ru"], ["pvp"], 2, "approved", 4.8, 10),
        MentorStub(2, 20, "ark_se", "Low", "UTC+3", ["ru"], ["taming"], 2, "approved", 3.2, 20),
        MentorStub(3, 30, "ark_se", "WrongLanguage", "UTC+3", ["en"], ["pvp"], 2, "approved", 5.0, 99),
        MentorStub(4, 40, "ark_se", "WrongTimezone", "UTC-3", ["ru"], ["pvp"], 2, "approved", 5.0, 99),
        MentorStub(5, 50, "ark_se", "Full", "UTC+3", ["ru"], ["pvp"], 1, "approved", 5.0, 99),
        MentorStub(6, 60, "ark_se", "Pending", "UTC+3", ["ru"], ["pvp"], 2, "pending", 5.0, 99),
    ]

    matches = find_matching_mentors(newbie, mentors, active_session_counts={5: 1})

    assert [match.mentor.game_nick for match in matches] == ["Top", "Low"]
    assert matches[0].matched_specializations == ("pvp",)
    assert matches[0].timezone_delta == 2


def test_parse_utc_offset_and_delta() -> None:
    assert parse_utc_offset("UTC") == 0
    assert parse_utc_offset("UTC+3") == 3
    assert parse_utc_offset("UTC-5") == -5
    assert timezone_delta("UTC+3", "UTC-1") == 4


@pytest.mark.parametrize("value", ["GMT+3", "UTC+15", "UTC++3"])
def test_parse_utc_offset_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_utc_offset(value)
