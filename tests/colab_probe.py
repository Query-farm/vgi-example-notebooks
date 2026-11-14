"""Install into a preloaded Colab-like kernel and verify SVG without a restart.

Run with the reported Colab dependency versions installed, passing a candidate wheel.
This is a compatibility simulation, not a hosted Google Colab session.
"""

from importlib.metadata import version
import io
import json
import subprocess
import sys

import ipykernel
import jupyter_client
import matplotlib.pyplot as plt
import matplotlib.text
import pandas
from IPython.core.interactiveshell import InteractiveShell


def main():
    distributions = ("ipykernel", "pandas", "jupyter-client", "matplotlib", "matplotlib-inline", "ipython")
    before = {name: version(name) for name in distributions}
    text_class = matplotlib.text.Text
    assert ipykernel.__version__ == before["ipykernel"]
    assert jupyter_client.__version__ == before["jupyter-client"]
    assert pandas.__version__ == before["pandas"]
    installed = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", sys.argv[1]],
        capture_output=True,
        text=True,
        check=False,
    )
    assert installed.returncode == 0, installed.stdout + installed.stderr
    assert "dependency conflicts" not in installed.stderr, installed.stderr
    after = {name: version(name) for name in distributions}
    assert before == after, {"before": before, "after": after}
    subprocess.run([sys.executable, "-m", "pip", "check"], check=True)

    from vgi_notebooks import check_runtime, theme
    from vgi_notebooks.runtime import load_sql

    check_runtime()
    shell = InteractiveShell.instance()
    load_sql(shell)
    theme()
    assert matplotlib.text.Text is text_class
    fig, ax = plt.subplots()
    ax.plot([0, 1, 2], [1, 3, 2])
    ax.set_title("SVG with Colab's existing libraries")
    output = io.StringIO()
    fig.savefig(output, format="svg")
    assert "<svg" in output.getvalue()
    plt.close(fig)
    print(json.dumps({"versions_preserved": after, "svg_rendered": True, "restart_required": False}))


if __name__ == "__main__":
    main()
