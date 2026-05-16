from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Specialization:
    key: str
    label: str
    description: str = ""


@dataclass(frozen=True)
class ReviewFieldSet:
    mentor_tags: tuple[str, ...] = field(default_factory=tuple)
    newbie_tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GamePlugin:
    key: str
    name: str
    mentor_nick_label: str
    newbie_nick_label: str
    specializations: tuple[Specialization, ...]
    safety_rules: tuple[str, ...]
    review_tags: ReviewFieldSet
    default_session_days: int = 14
    quarantine_sessions: int = 3

    def specialization_labels(self) -> dict[str, str]:
        return {item.key: item.label for item in self.specializations}

    def validate_specializations(self, values: list[str]) -> list[str]:
        allowed = self.specialization_labels()
        normalized = [value.strip().lower() for value in values if value.strip()]
        unknown = [value for value in normalized if value not in allowed]
        if unknown:
            raise ValueError(f"Unknown specializations for {self.key}: {', '.join(unknown)}")
        return normalized

    def format_specializations(self, values: list[str] | tuple[str, ...]) -> str:
        labels = self.specialization_labels()
        return ", ".join(labels.get(value, value) for value in values) or "—"
