"""Preloaded kernels must not continue with replaced or conflicting libraries."""

import subprocess
import sys
from types import SimpleNamespace

import pytest

from vgi_notebooks import compatibility


def test_package_import_does_not_load_plotting_or_dataframe_libraries():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, vgi_notebooks; assert 'matplotlib' not in sys.modules; "
            "assert 'pandas' not in sys.modules; vgi_notebooks.check_runtime()",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_library_replaced_on_disk_requires_a_restart(monkeypatch):
    monkeypatch.setitem(sys.modules, "pandas", SimpleNamespace(__version__="0.0.0"))
    with pytest.raises(RuntimeError, match="Restart session"):
        compatibility.check_runtime()


def test_old_text_class_detected_even_if_matplotlib_reports_new_version(monkeypatch):
    monkeypatch.setitem(sys.modules, "matplotlib", SimpleNamespace(__version__="3.11.2"))
    monkeypatch.setitem(sys.modules, "matplotlib.text", SimpleNamespace(Text=type("OldText", (), {})))
    original = compatibility.version
    monkeypatch.setattr(
        compatibility, "version", lambda name: "3.11.2" if name == "matplotlib" else original(name)
    )
    with pytest.raises(RuntimeError, match="Text class predates"):
        compatibility.check_runtime()


def test_previously_broken_colab_requires_fresh_runtime(monkeypatch):
    monkeypatch.setattr(compatibility, "requires", lambda name: ["ipykernel==6.17.1", "pandas==2.2.3"])
    monkeypatch.setattr(
        compatibility, "version", lambda name: {"ipykernel": "7.4.0", "pandas": "2.3.3"}[name]
    )
    with pytest.raises(RuntimeError, match="Disconnect and delete runtime"):
        compatibility.check_runtime()
