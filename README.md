# VGI example notebooks

Shared tooling and the authoring standard for Query.Farm's executable worker examples.
Kalshi and TLSFP provide the first supported examples. Worker notebooks pin a shared-tooling release.

Worker repositories keep their notebooks, small example-specific helpers, fixtures,
locked environment, and a short README index. This project owns the standard,
canonical header/footer, plotting theme, execution runner and output checks. The
intended consumer is a released Python package; Git submodules are not required.

GitHub is the reading surface. Google Colab is an execution option linked with its
official badge. Notebook setup must be short when fully expanded, because GitHub's
renderer does not apply editor source-folding metadata. SQL connections remain visible.

See [the pilot standard](docs/standard.md) and [Kalshi's narrative plan](docs/kalshi.md).

## Run an example

Install this package with the `[runner]` extra at a published tag through uv or pip, then run `vgi-notebooks`
from the worker's notebooks directory. Override parameters with a separate output:

```sh
uv run vgi-notebooks --parameters '{"BAND_CENTS":10}' --output-dir artifacts/band-10
```

A Colab notebook installs the package in its first setup cell. `prepare("kalshi")`
uses companions from a normal checkout when present, or retrieves the registry's
immutable, hash-verified helper and public fixture files into an example cache.
The worker runtime is separate and its release-based ATTACH remains visible.
The renderer needs no custom JavaScript. See `src/vgi_notebooks/registry/` for the
exact public sources and hashes. No account credentials or Drive mount are needed.

Hosted Colab opens GitHub notebooks but does not bring along their filesystem; this
bootstrap supplies that missing step. A link and clean-runtime tests do not imply
that a hosted Colab session was manually exercised.

Colab installs the base package, without `[runner]`. Compatible versions of pandas,
Matplotlib and IPython already supplied by Colab are retained. Kernel-management
packages belong only to the local runner extra. A runtime check detects libraries
replaced while the session was running before importing the plotting helpers.
If an older example already installed conflicting Colab dependencies, save your work
and use **Runtime → Disconnect and delete runtime**, reconnect, and run the updated
notebook. A session restart alone does not undo installed packages.

For development, use `uv sync --locked --extra runner` and `uv run --extra runner pytest`.
CI also installs into an environment with the reported Colab dependency versions,
preloads plotting and kernel libraries, and verifies unchanged versions, `pip check`
and SVG rendering without a restart.

## Coverage and shared SQL setup

The fleet target is 100% of public named SQL functions/tables for workers with up to
ten objects, and at least 50% for larger catalogs. The [coverage evidence format](docs/coverage.md)
keeps actual execution, editorial review, catalog completeness and current/release
differences explicit. It does not count static references as verified examples.

`connect(globals())` initializes SQL magics with a Haybarn connection isolated from
saved SQL credentials and JupySQL default connections. It returns a session to close
at the end. Worker `INSTALL`, `LOAD` and release-based `ATTACH` remain visible SQL.
