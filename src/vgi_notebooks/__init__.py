"""Small shared tools for executable, GitHub-readable VGI examples."""

from .bootstrap import prepare
from .presentation import finish, prose, theme

__all__ = ["finish", "prose", "theme", "prepare"]
