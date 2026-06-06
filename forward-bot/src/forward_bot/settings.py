"""Deprecated module. Use forward_bot.config instead."""
import warnings
from forward_bot.config import Settings

warnings.warn(
    "forward_bot.settings is deprecated. Use forward_bot.config instead.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["Settings"]
