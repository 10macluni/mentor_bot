from __future__ import annotations

from bot.plugins.base import GamePlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, GamePlugin] = {}

    def register(self, plugin: GamePlugin) -> None:
        self._plugins[plugin.key] = plugin

    def get(self, key: str) -> GamePlugin:
        try:
            return self._plugins[key]
        except KeyError as exc:
            known = ", ".join(sorted(self._plugins)) or "none"
            raise KeyError(f"Unknown game plugin '{key}'. Registered plugins: {known}") from exc

    def all(self) -> tuple[GamePlugin, ...]:
        return tuple(self._plugins.values())


registry = PluginRegistry()
