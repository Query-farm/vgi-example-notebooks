"""Small shared tools for executable, GitHub-readable VGI examples."""

from .bootstrap import prepare
from .compatibility import check_runtime
from .session import connect

__all__ = ["finish", "prose", "theme", "prepare", "check_runtime", "connect"]


def __getattr__(name):
    # Runtime checks must run before importing any plotting/dataframe libraries.
    if name in {"finish", "prose", "theme"}:
        check_runtime()
        from . import presentation

        return getattr(presentation, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
