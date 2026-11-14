"""The shared connection must isolate saved secrets and close cleanly."""

import json
import sys

import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager


def test_real_sql_session_uses_disposable_secrets_and_retains_sql_access(tmp_path):
    code = """
from pathlib import Path
from datetime import timedelta
from IPython import get_ipython
from unittest.mock import patch
from sql.connection import ConnectionManager
from vgi_notebooks import connect
shell = get_ipython()
with patch.object(ConnectionManager, 'load_default_connection_from_file_if_any', side_effect=AssertionError('Must not open a saved default connection')):
    session = connect(shell.user_ns)
con = shell.user_ns['con']
assert con.execute('SELECT 6 * 7').fetchall() == [(42,)]
assert con.execute("SELECT current_setting('TimeZone')").fetchone() == ('UTC',)
for _ in range(2):
    result = shell.run_cell_magic('sql', '', "SELECT current_setting('TimeZone') AS zone, TIMESTAMPTZ '2026-11-14 00:00:00+00' AS instant")
    assert result.iloc[0]['zone'] == 'UTC'
    assert result.iloc[0]['instant'].utcoffset() == timedelta(0)
    assert result.iloc[0]['instant'].hour == 0
assert con.execute('SELECT * FROM duckdb_secrets()').fetchall() == []
settings = dict(con.execute("SELECT name, value FROM duckdb_settings() WHERE name IN ('secret_directory', 'allow_persistent_secrets')").fetchall())
assert settings['allow_persistent_secrets'] == 'false'
directory = Path(settings['secret_directory'])
assert directory.is_dir()
assert shell.run_cell_magic('sql', '', 'SELECT 1 AS value').iloc[0]['value'] == 1
session.close()
session.close()
assert not directory.exists()
"""
    kernel = tmp_path / "isolated"
    kernel.mkdir()
    (kernel / "kernel.json").write_text(
        json.dumps(
            {
                "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                "display_name": "Session regression",
                "language": "python",
            }
        )
    )
    manager = KernelManager(
        kernel_name="isolated", kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(tmp_path)])
    )
    notebook = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(code)])
    NotebookClient(notebook, km=manager, timeout=60).execute(cleanup_kc=True)
