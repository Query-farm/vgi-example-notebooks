"""Publication checks for the shared GitHub notebook standard."""

import re
from .branding import header, footer

# PII v0.4.0 omits its required English model from runtime dependencies.
# Permit only this released worker + model combination, in the worker process;
# this is not permission for transitive dependency override stacks.
_PII_MODEL_LAUNCHER = (
    "uvx --python 3.13 --from git+https://github.com/Query-farm/vgi-pii@v0.4.0 "
    "--with https://github.com/explosion/spacy-models/releases/download/"
    "en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl vgi-pii-worker"
).split()


def validate_presentation(notebook):
    """Require canonical branding and a readable release-based SQL connection."""
    descriptor = notebook.metadata.get("vgi_example")
    if not descriptor:
        raise ValueError("Notebook needs vgi_example repository/path metadata")
    cells = notebook.cells
    if not cells or cells[0].cell_type != "markdown" or cells[-1].cell_type != "markdown":
        raise ValueError("First and last cells must contain canonical branding")
    expected = header(descriptor["repository"], descriptor["path"])
    if not cells[0].source.startswith(expected):
        raise ValueError("Header differs from the shared Query.Farm / VGI / Colab standard")
    if cells[-1].source.strip() != footer().strip():
        raise ValueError("Footer differs from the shared Query.Farm standard")
    connections = [
        c
        for c in cells
        if c.cell_type == "code"
        and c.source.lstrip().startswith("%%sql")
        and re.search(r"\bATTACH\b", c.source, re.I)
    ]
    if not connections:
        raise ValueError("A visible SQL ATTACH cell is required")
    for cell in connections:
        if cell.metadata.get("jupyter", {}).get("source_hidden"):
            raise ValueError("SQL connection cell must remain visible")
        locations = re.findall(r"\bLOCATION\s+'([^']+)'", cell.source, re.I)
        if not locations:
            raise ValueError("SQL connection must use a literal LOCATION")
        for location in locations:
            source_revision = re.search(r"@[a-f0-9]{40}(?:\s|$)", location)
            extra_dependency = re.search(r"--with(?:\s|=)", location)
            required_pii_model = location.split() == _PII_MODEL_LAUNCHER
            if source_revision or (extra_dependency and not required_pii_model):
                raise ValueError("Use a released worker and keep dependency overrides out of ATTACH")
