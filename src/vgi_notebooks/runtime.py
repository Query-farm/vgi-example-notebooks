"""Notebook initialization with a narrow workaround for JupySQL's docstring warning."""

import re
import warnings


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
