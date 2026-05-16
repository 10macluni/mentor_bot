import pytest

from bot.services.reputation import calculate_mentor_badges, validate_rating


def test_calculate_mentor_badges() -> None:
    assert calculate_mentor_badges(0, 0) == []
    assert calculate_mentor_badges(5, 4.0) == ["🥉 Бронзовый ментор"]
    assert calculate_mentor_badges(15, 4.0)[-1] == "🥈 Серебряный ментор"
    assert calculate_mentor_badges(30, 4.0)[-1] == "🥇 Золотой ментор"
    assert calculate_mentor_badges(50, 4.5)[-1] == "💎 Легендарный ментор"


@pytest.mark.parametrize("rating", [1, 3, 5])
def test_validate_rating_accepts_valid_values(rating: int) -> None:
    assert validate_rating(rating) == rating


@pytest.mark.parametrize("rating", [0, 6])
def test_validate_rating_rejects_invalid_values(rating: int) -> None:
    with pytest.raises(ValueError):
        validate_rating(rating)
