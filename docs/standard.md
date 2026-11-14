# GitHub and Colab notebook standard

## First and final cells

Every first cell uses the same order: linked Query.Farm Strata Sun wordmark, linked
VGI product mark, the worker's proper title as a linked **H1**, its published
subtitle as a readable paragraph, Open in Colab and source links, then the notebook's
narrative title as **H2** and its question. Sections within that story use **H3**.
Marks retain their official colors/proportions. Query.Farm remains the
publisher; VGI is the product. Use consistent dimensions and alignments across
workers. Use the catalog's `vgi.title` and `vgi.subtitle`, recording their source
and release; use its published description if a subtitle is absent. Do not generate
a display title from the repository slug. For example, BGP uses **BGP MRT Decoder**,
followed by its published sentence about querying RouteViews and RIPE RIS archives.
The linked worker title points directly to the worker's GitHub repository,
so a notebook read outside its checkout still identifies the software it demonstrates.
The final cell repeats the linked Query.Farm wordmark and named worker repository
link after cleanup. Generate these cells with
`header(repository, notebook_path, title=title, subtitle=subtitle)` and
`footer(repository)` from the shared branding module. Store the same `title` and
`subtitle` in notebook `vgi_example` metadata so publication can check consistency.
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
compatibility. For registered Bun releases without published executables,
`vgi-bun-worker Query-farm/vgi-open-meteo@v0.4.0` downloads the official
checksum-verified Bun runtime on macOS/glibc Linux, verifies the Git release tag,
and installs the unchanged frozen lock with install hooks disabled. It interprets
the released TypeScript directly; it does not build the worker. The managed cache
is separate from notebook dependencies and requires Git plus network access on
the first run. Setup diagnostics use stderr, leaving stdout for VGI.
 A long transitive --with list does not belong in teaching SQL.
The PII v0.4.0 release needs one explicitly documented exception: its English
spaCy model is absent from runtime dependencies. The presentation validator accepts
only the exact released worker plus official en_core_web_sm 3.8.0 wheel command;
extra transitive overrides remain rejected. The model installs inside the isolated
worker environment, preserving the notebook kernel libraries.

Use a released shared package rather than a submodule. Keep the full standard and
runner here; keep only a notebook-specific README/index in each worker repo. Worker
fixtures and analytical helpers remain with their worker. A Colab bootstrap must
install dependencies and retrieve hash-verified companions without manual cloning.
Keep setup and VGI connection separate so the connection stays understandable.

Inside Colab install only the base shared package. The `[runner]` extra is for local
publication environments; never replace Colab's kernel or Jupyter client to execute
a notebook already running there. Accept compatible preinstalled plotting and data
libraries, while local `uv.lock` files preserve exact publication versions. Call
`check_runtime()` before loading helpers to detect stale imported libraries or a
Colab environment damaged by earlier installs. Test with libraries already imported,
not only in a bare virtual environment.

## Output

Use SVG MIME output for charts. The publication runner also saves content-addressed
SVG files under notebooks/charts and adds an image reference for GitHub, whose native
SVG output renderer currently adds byte-string artifacts. Colab and Jupyter reruns
produce native SVG. Experiment copies retain native SVG without unpublished image
links. Commit generated chart files with the default notebook and retain older hashes
so prior notebook revisions still resolve. Export PNG review artifacts when needed. SVG alone does not fix poor chart design:
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

For notebook-only changes, reuse successful source CI for the unchanged worker
revision. Do not rebuild the worker, rerun its entire unit/transport test suite,
or dispatch source/container CI merely to publish examples. Run additional source
checks when worker code changes, a concrete runtime discrepancy needs investigation,
or an applicable repository rule requires them. Keep existing source failures
separate from notebook regressions.

Execute every saved default and its meaningful parameter experiment. Exercise a
fresh notebook-only bootstrap with libraries already loaded for each distinct
launcher and companion path; notebooks sharing that path do not each need an
identical dependency-installation test. Review all changed figures and verify the
published GitHub SVGs. Repeat checks only after relevant changes or unresolved
failures. Batch stable companion registrations into shared releases when practical;
registry-only additions need companion hash verification, bootstrap tests and a
package build, with the shared CI providing its full checks.

## Fleet surface coverage

Assess every worker's complete public SQL catalog. A worker with up to ten named
functions/tables requires **100%** coverage; larger workers require at least **50%**
(round up to a whole object). Count each `(schema, name)` once, retaining overloads
and table/function aliases as alternate access forms. Authentication requirements,
write capability and difficult inputs do not remove an object from the denominator.

Each covered object needs a successful visible SQL invocation used in a focused
narrative, with returned results and an interpretation. Merely mentioning a name,
listing a catalog or running an empty diagnostic does not establish that coverage.
Keep the current public source interface and selected release interface separate;
unreleased functions remain explicit coverage gaps. Record review and execution
evidence using [coverage.json and its artifacts](coverage.md).

The shared `connect(globals())` helper creates a disposable empty SQL-secret
directory and registers the explicit Haybarn connection with `TimeZone=UTC` at
creation. It puts the active kernel's scripts directory on PATH before starting
Haybarn, so installed launchers work from kernelspecs whose virtualenv was not
shell-activated. JupySQL creates cursors, so a `SET TimeZone` inside one SQL cell alone
does not establish the timezone for later cells. Convert explicitly when showing
a different zone. SQL extension loading
does not open a saved JupySQL default connection. Keep worker ATTACH calls visible;
use `AUTH 'off'` where a worker advertises that option, and omit unsupported options
for local computation workers.
