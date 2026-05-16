from bot.plugins.ark_se.plugin import ARK_SE_PLUGIN
from bot.plugins.registry import registry

registry.register(ARK_SE_PLUGIN)

__all__ = ["registry", "ARK_SE_PLUGIN"]
