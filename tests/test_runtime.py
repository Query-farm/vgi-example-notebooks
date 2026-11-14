"""The documented parser warning is narrow; unrelated warnings remain visible."""

import os
import subprocess
import sys
import warnings

import pytest

from vgi_notebooks.runtime import load_sql


def test_known_escape_only_and_filter_restored():
    class Shell:
        def run_line_magic(self, name, arg):
            if name == "load_ext":
                warnings.warn_explicit("invalid escape sequence '\\:'", SyntaxWarning, "/tmp/sql/parse.py", 1)
                warnings.warn("Unrelated warning", RuntimeWarning)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        load_sql(Shell())
        assert len(caught) == 1 and caught[0].category is RuntimeWarning
        warnings.warn_explicit("invalid escape sequence '\\:'", SyntaxWarning, "/tmp/unrelated.py", 1)
        assert len(caught) == 2 and caught[1].category is SyntaxWarning


@pytest.mark.parametrize(
    ("filename", "message", "expected"),
    [
        ("/env/site-packages/sql/parse.py", "invalid escape sequence '\\:'", 0),
        (
            r"C:\env\Lib\site-packages\sql\parse.py",
            "'\\:' is an invalid escape sequence. Use a raw string.",
            0,
        ),
        ("/env/site-packages/other/parse.py", "invalid escape sequence '\\:'", 1),
        ("/env/site-packages/sql/parse.py", "invalid escape sequence '\\q'", 1),
    ],
)
def test_filters_only_parser_filename_and_known_message(filename, message, expected):
    class Shell:
        def run_line_magic(self, name, arg):
            if name == "load_ext":
                warnings.warn_explicit(message, SyntaxWarning, filename, 7)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        load_sql(Shell())
    assert len(caught) == expected
    if expected:
        assert caught[0].filename == filename
        assert caught[0].lineno == 7


def test_loader_errors_propagate_and_captured_warnings_are_reemitted():
    class Shell:
        def run_line_magic(self, name, arg):
            assert name == "load_ext"
            warnings.warn_explicit("invalid escape sequence '\\:'", SyntaxWarning, "/tmp/sql/parse.py", 1)
            warnings.warn("Unrelated warning before failure", UserWarning)
            raise ValueError("extension initialization failed")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError, match="extension initialization failed"):
            load_sql(Shell())
    assert len(caught) == 1
    assert caught[0].category is UserWarning


def test_unrelated_warning_error_policy_is_preserved():
    class Shell:
        def run_line_magic(self, name, arg):
            if name == "load_ext":
                warnings.warn_explicit("invalid escape sequence '\\:'", SyntaxWarning, "/tmp/other.py", 1)

    with warnings.catch_warnings():
        warnings.simplefilter("error", SyntaxWarning)
        with pytest.raises(SyntaxWarning):
            load_sql(Shell())


@pytest.mark.skipif(
    sys.version_info < (3, 12), reason="The upstream compiler warning is SyntaxWarning on 3.12+"
)
def test_real_sql_extension_cold_import_has_no_warnings(tmp_path):
    code = """
import warnings
from IPython.core.interactiveshell import InteractiveShell
from vgi_notebooks.runtime import load_sql
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter('always')
    load_sql(InteractiveShell.instance())
assert not caught, [(str(w.message), w.filename) for w in caught]
"""
    env = dict(os.environ, PYTHONPYCACHEPREFIX=str(tmp_path / "cold-pycache"), PLOOMBER_STATS_ENABLED="false")
    result = subprocess.run(
        [sys.executable, "-B", "-c", code], env=env, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stdout + result.stderr
