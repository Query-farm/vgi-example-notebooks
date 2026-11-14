# GitHub and Colab notebook standard — Kalshi pilot

## First and final cells

Every first cell uses the same order: linked Query.Farm Strata Sun wordmark, linked
VGI product mark, Open in Colab and source links, then the narrative title and
question. Marks retain their official colors/proportions. Query.Farm remains the
publisher; VGI is the product. Use consistent dimensions and alignments across
workers. The final cell repeats the linked Query.Farm wordmark after cleanup.
Colab must display branding before execution; relative companion paths need a
renderer-compatible solution rather than assuming Colab cloned the repository.

## Reader-visible code

Show parameters, dependency/bootstrap commands, VGI INSTALL/LOAD/ATTACH and analytical
SQL. Keep bootstrap brief; use shared implementation for secret isolation, SQL magic
initialization and chart formatting. Keep editor folding metadata as an editor aid.
Never rely on it to hide scaffolding from GitHub. Markdown <details> sections are
appropriate for optional prose, not a workaround for hiding executable cell inputs.

## Runtime and dependencies

Pin the worker to a published release, prefer a release binary when available,
and otherwise use a short uvx Git-tag command. The release/package owns dependency
compatibility. A long transitive --with list does not belong in teaching SQL.

Use a released shared package rather than a submodule. Keep the full standard and
runner here; keep only a notebook-specific README/index in each worker repo. Worker
fixtures and analytical helpers remain with their worker. A Colab bootstrap must
install dependencies and retrieve hash-verified companions without manual cloning.
Keep setup and VGI connection separate so the connection stays understandable.

## Output

Use SVG MIME output for charts. Export SVG review artifacts and high-resolution PNG
fallbacks where a viewer requires them. SVG alone does not fix poor chart design:
use readable text, light grids, meaningful units, direct labels, a consistent
palette and scales suited to the narrative. Avoid squeezing a local effect into
a full-range chart dominated by distant values; use clearly labeled comparison panels.

Saved outputs must contain no traceback, unexpected warnings, machine-specific
paths, progress logs or dependency-install noise. Narrow handling of documented
upstream warnings is permitted; do not suppress runtime errors or arbitrary warnings.
Validate cold import paths as well as cached environments.

## Narrative and validation

Give each notebook a concrete question, returned-data-derived interpretation and
one meaningful parameter experiment. A rich API merits several independent stories,
not a single exhaustive catalog dump. Materialize API calls before display, label
real recordings and synthetic data truthfully, isolate SQL credentials before
connection creation and retain provenance. Test defaults, experiments, empty/missing
cases where relevant, fresh companion-only execution and supported live reads.
A working Colab link is distinct from a hosted-Colab execution test; report both honestly.
