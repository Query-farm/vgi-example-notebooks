# VGI example notebooks

Shared tooling and the authoring standard for Query.Farm's executable worker examples.
The first supported example is Kalshi. Worker notebooks pin a shared-tooling release.

Worker repositories keep their notebooks, small example-specific helpers, fixtures,
locked environment, and a short README index. This project owns the standard,
canonical header/footer, plotting theme, execution runner and output checks. The
intended consumer is a released Python package; Git submodules are not required.

GitHub is the reading surface. Google Colab is an execution option linked with its
official badge. Notebook setup must be short when fully expanded, because GitHub's
renderer does not apply editor source-folding metadata. SQL connections remain visible.

See [the pilot standard](docs/standard.md) and [Kalshi's narrative plan](docs/kalshi.md).

## Run an example

Install this package at a published tag through uv or pip, then run `vgi-notebooks`
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
