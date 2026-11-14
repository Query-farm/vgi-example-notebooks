"""Shared SQL setup that isolates notebook kernels from saved SQL credentials."""

from tempfile import TemporaryDirectory
import os
import sysconfig

from .compatibility import check_runtime


class NotebookSession:
    """Own a Haybarn connection and its disposable, empty secret directory."""

    def __init__(self, namespace):
        check_runtime()
        # A kernelspec can name a virtualenv Python without activating its bin
        # directory. Make this kernel's installed console tools visible to VGI.
        scripts = sysconfig.get_path("scripts")
        entries = os.environ.get("PATH", "").split(os.pathsep)
        os.environ["PATH"] = os.pathsep.join([scripts, *(p for p in entries if p != scripts)])
        import haybarn
        from IPython import get_ipython
        from .runtime import load_sql

        shell = get_ipython()
        if shell is None:
            raise RuntimeError("Notebook SQL setup requires an IPython/Jupyter kernel")
        os.environ["PLOOMBER_STATS_ENABLED"] = "false"
        self._secrets = TemporaryDirectory(prefix="vgi-notebook-secrets-")
        self.connection = None
        try:
            self.connection = haybarn.connect(
                config={
                    "secret_directory": self._secrets.name,
                    "allow_persistent_secrets": False,
                    "TimeZone": "UTC",
                }
            )
            if self.connection.execute("SELECT * FROM duckdb_secrets()").fetchall():
                raise RuntimeError("Notebook connection must start without SQL secrets")
            namespace["con"] = self.connection
            load_sql(shell)
            shell.run_line_magic("sql", "con")
            shell.run_line_magic("matplotlib", "inline")
        except BaseException:
            self.close()
            raise

    def close(self):
        """Release the worker processes and disposable SQL configuration."""
        try:
            if self.connection is not None:
                self.connection.close()
                self.connection = None
        finally:
            self._secrets.cleanup()


def connect(namespace):
    """Initialize SQL magics; keep worker INSTALL/LOAD/ATTACH in visible SQL cells."""
    return NotebookSession(namespace)
