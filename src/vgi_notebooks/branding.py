"""Canonical publisher/product header and publisher footer for worker notebooks."""

from html import escape
from pathlib import PurePosixPath
from urllib.parse import quote

ASSETS = "https://raw.githubusercontent.com/Query-farm/vgi-example-notebooks/v0.1.1/assets"


def header(repository, notebook_path):
    """Use one fixed logo order, sizing, and hosted-notebook action."""
    colab = f"https://colab.research.google.com/github/{repository}/blob/main/{quote(notebook_path)}"
    notes = f"https://github.com/{repository}/blob/main/{quote(str(PurePosixPath(notebook_path).parent))}/README.md"
    return f'''<p><a href="https://query.farm/"><img src="{ASSETS}/query-farm-strata-sun.svg" alt="Query.Farm — Strata Sun" width="252"></a></p>

<p><a href="https://query.farm/vgi/"><img src="{ASSETS}/vgi-logo.png" alt="VGI" width="112"></a></p>

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)]({escape(colab)})

[Query.Farm](https://query.farm/) · [VGI](https://query.farm/vgi/) · [Example notes]({escape(notes)})
'''


def footer():
    """Close the notebook with the same linked publisher wordmark."""
    return f'''<a href="https://query.farm/"><img src="{ASSETS}/query-farm-strata-sun.svg" alt="Query.Farm — Strata Sun" width="252"></a>

[Query.Farm](https://query.farm/) · [VGI](https://query.farm/vgi/)
'''
