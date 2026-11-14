"""Notebook initialization with a narrow workaround for JupySQL's docstring warning."""

import re
import warnings
from unittest.mock import patch


_KNOWN_ESCAPE = re.compile(
    r"""(?:invalid escape sequence ['"]\\:['"]|['"]\\:['"] is an invalid escape sequence).*"""
)


def _known_parser_warning(warning):
    filename = "/" + warning.filename.replace("\\", "/")
    return (
        warning.category is SyntaxWarning
        and filename.endswith("/sql/parse.py")
        and _KNOWN_ESCAPE.match(str(warning.message)) is not None
    )


def load_sql(ipython):
    """Load SQL magics without suppressing unrelated warnings or query errors."""
    captured = []
    try:
        with warnings.catch_warnings(record=True) as captured:
            # Compiler warnings carry the source filename, not a reliable module name.
            warnings.simplefilter("always", SyntaxWarning)
            from sql import display
            from sql.connection import ConnectionManager

            message, message_html = display.message, display.message_html

            def without_config_tip(text, *args, **kwargs):
                if str(text).startswith(
                    ("Tip: You may define configurations in ", "Did not find user configurations in ")
                ):
                    return
                return message(text, *args, **kwargs)

            def without_config_link(text, *args, **kwargs):
                if str(text) == (
                    "Please review our <a href='https://jupysql.ploomber.io/en/latest/api/"
                    "configuration.html#loading-from-a-file'>configuration guideline</a>."
                ):
                    return
                return message_html(text, *args, **kwargs)

            # These optional configuration hints include local filesystem paths.
            # Keep all other messages, warnings and exceptions visible.
            with (
                patch.object(display, "message", without_config_tip),
                patch.object(display, "message_html", without_config_link),
                # The notebook supplies its isolated connection explicitly.
                patch.object(
                    ConnectionManager, "load_default_connection_from_file_if_any", return_value=None
                ),
            ):
                ipython.run_line_magic("load_ext", "sql")
    finally:
        for warning in captured:
            if not _known_parser_warning(warning):
                warnings.warn_explicit(
                    warning.message,
                    warning.category,
                    warning.filename,
                    warning.lineno,
                    source=warning.source,
                )
    ipython.run_line_magic("config", "SqlMagic.autopandas = True")
    ipython.run_line_magic("config", "SqlMagic.feedback = False")
    ipython.run_line_magic("config", "SqlMagic.displaycon = False")
