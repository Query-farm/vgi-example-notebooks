# Notebook surface coverage evidence, version 1

Coverage counts one logical public SQL surface per **(schema path, name)**. Overloads
and a table with a same-named function alias count once; their kinds and signatures
are retained. Authentication requirements and write capability never remove a surface
from the denominator. A verified catalog of 1–10 surfaces requires all of them; a
larger catalog requires at least `ceil(count / 2)`.

This is coverage of focused, interpreted examples, not a count of strings in source.
The validator requires catalog evidence, successful execution receipts, visible SQL,
result outputs, narrative references, and explicit editorial approval. A scanner or
saved execution count alone produces a **candidate**, never verified coverage.

## API and files

```python
import json
from pathlib import Path
from vgi_notebooks.coverage import validate_coverage

root = Path("notebooks")
report = validate_coverage(json.loads((root / "coverage.json").read_text()), root)
assert report["meets_target"], report
```

The module uses only the standard library; it does not add runner dependencies to
the Colab core. All artifact paths below are relative to `root`. Absolute paths,
parent traversal, escaping symlinks and SHA-256 mismatches fail verification. Use
lowercase full SHA-256 hashes. Timestamps must include their timezone.

The top-level manifest is:

```json
{
  "schema_version": 1,
  "catalogs": {
    "released": {
      "path": "coverage/catalog-release.json",
      "sha256": "<snapshot SHA-256>",
      "review": {
        "status": "approved",
        "reviewer": "<reviewer identity>",
        "reviewed_at": "2026-11-14T17:00:00Z",
        "catalog_sha256": "<same snapshot SHA-256>",
        "notes": "<How the full public interface, including authenticated and write APIs, was checked>"
      }
    },
    "current": {"status": "unknown", "reason": "<Specific missing current-main catalog evidence>"}
  },
  "notebooks": [
    {
      "path": "01_example.ipynb",
      "sha256": "<final saved notebook SHA-256>",
      "execution": {"path": "coverage/run-01.json", "sha256": "<receipt SHA-256>"}
    }
  ],
  "examples": [
    {
      "object": {"schema": "main", "name": "convert"},
      "notebook": "01_example.ipynb",
      "sql": [{"cell": "conversion-query", "reference": "units.main.convert"}],
      "narrative_cells": ["question-and-inputs"],
      "result_cells": ["conversion-query"],
      "interpretation_cells": ["conversion-finding"],
      "review": {
        "status": "approved",
        "reviewer": "<reviewer identity>",
        "reviewed_at": "2026-11-14T17:10:00Z",
        "notebook_sha256": "<final saved notebook SHA-256>",
        "catalog_sha256": ["<each catalog snapshot to which this reviewed example applies>"],
        "purpose": "<The concrete question this invocation helps answer>",
        "finding": "<What the returned result establishes, and its limits>"
      }
    }
  ]
}
```

Use a full descriptor for `current` when its evidence is available. Additional catalog
labels may describe older runtimes used by other notebooks. Every verified snapshot
must refer to the same worker repository. The report always separates `released`
and `current`; its top-level target is the **current public interface**. Missing,
partial, empty or unreviewed catalogs have `denominator: null`, not an inferred zero
or a passing percentage.

## Complete catalog snapshot

```json
{
  "schema_version": 1,
  "repository": "Query-farm/vgi-units",
  "revision": "<immutable source revision or recorded release identity>",
  "captured_at": "2026-11-14T16:50:00Z",
  "default_schema": "main",
  "scope": "all_public_functions_and_tables",
  "complete": true,
  "evidence": [
    {"path": "coverage/functions.json", "sha256": "<hash>", "description": "Complete worker-filtered duckdb_functions() export"},
    {"path": "coverage/tables.json", "sha256": "<hash>", "description": "Complete worker-filtered duckdb_tables() export, including an explicit empty result if applicable"}
  ],
  "objects": [
    {
      "schema": "main", "name": "convert", "kind": "function",
      "signatures": ["convert(DOUBLE, VARCHAR, VARCHAR)"],
      "authentication": "none", "access": "read"
    }
  ]
}
```

Schema may be a string or an array of path components. `kind` is `function` or
`table`; normalize a public view to `table` and retain its `VIEW` access form in
`signatures`. Views are public relation surfaces and must not be excluded merely
because `duckdb_tables()` omits them. Repeated overload/alias rows are merged case-insensitively using DuckDB's
identifier semantics. `authentication` accepts `none`, `optional`, `required`, or
`unknown`; `access` accepts `read`, `write`, `read_write`, or `unknown`. The latter
two fields may be omitted when not advertised and are then recorded as unknown;
the object still counts. There are no exclusion switches.

Collector JSON exports shaped as `{query, columns, rows}` are reconciled against the
snapshot whenever their columns include `database_name`, `schema_name`, and
`function_name`, `table_name`, or `view_name`. Collect complete worker-filtered
`duckdb_functions()`, `duckdb_tables()` and `duckdb_views()` exports, including empty
results. The validator reconciles their union; a view and table with the same
`(schema, name)` share one relation surface, and a same-named function alias also
shares that logical denominator entry. An omitted or invented exported object
invalidates the denominator. Function and physical-table exports remain required;
a view export cannot substitute for either. Older artifacts without a view export
remain accepted, with their explicit completeness review responsible for confirming
there are no unrecorded views. Argument exports are supplementary evidence, not a
replacement for full function/table/view exports.

Other evidence, such as a source registration listing for unreleased current-main
APIs, must still be present and hash-bound. Its completeness requires the explicit
catalog review; `collection_reconciled: false` makes the absence of a generic raw
export reconciliation visible. Reviewers must inspect actual registration and avoid
filters that omit credential-dependent, stateful, write, difficult or failing APIs.

## Successful execution receipt

The executor writes this only after the whole notebook has successfully run. Generate
it after final output formatting/publication so its notebook and output hashes match
the saved file. Do not manufacture a success receipt by scanning an existing notebook.

```json
{
  "schema_version": 1,
  "notebook_sha256": "<saved notebook SHA-256>",
  "catalog_sha256": "<snapshot of the actual executed worker runtime>",
  "worker_revision": "<exactly that snapshot's revision>",
  "status": "success",
  "executed_at": "2026-11-14T17:05:00Z",
  "engine": "Haybarn 2.0.0rc11 / VGI <revision>",
  "command": "<actual executor command>",
  "catalog_aliases": ["units"],
  "cells": [
    {
      "id": "conversion-query", "status": "success", "execution_count": 5,
      "source_sha256": "<exact joined UTF-8 source hash>",
      "outputs_sha256": "<canonical JSON outputs hash>"
    }
  ]
}
```

Include **every code cell exactly once**, including setup and cleanup. All need
positive execution counts, matching receipt counts/hashes, and no error outputs.
Failed or unexecuted cells invalidate the entire notebook's execution evidence.
Stable notebook cell IDs bind mappings and receipts without fragile positional indices.

`file_sha256(path)`, `cell_source_sha256(cell)` and `cell_outputs_sha256(cell)` implement
the hashes. Output hashing uses
`json.dumps(outputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` encoded
as UTF-8. `notebook_candidate_evidence(path)` collects these fingerprints but labels
its result `candidate` and does not provide a success status for any cell.

Read the final saved notebook with `json.loads(path.read_text())` when hashing its
outputs. `nbformat.read` normalizes multiline arrays into strings, which changes
the saved JSON representation and produces a different output hash.

## Mapping and editorial checks

SQL references must visibly occur in a mapped `%sql` or `%%sql` cell as an invocation,
using an executed catalog alias. Fully qualified references are preferred; omission
of the default schema is supported. Quoted identifiers work; references inside strings,
line/block comments or dollar-quoted strings do not count. Function references need a
call; table references need a relation/write target context. Python helper calls,
dynamic object names, parser hits and expected-error examples remain candidates.

### COPY handlers

A named COPY handler advertised in `duckdb_functions()` stays in the function
denominator. It can be demonstrated through visible `COPY` SQL instead of a direct
function call. Add the **actual executed runtime's** worker-filtered registration
export to that catalog snapshot's hash-bound `evidence` list:

```sql
SELECT * FROM vgi_copy_formats()
WHERE catalog_name = 'feed'
ORDER BY format_name, direction;
```

Keep the native `{query, columns, rows}` shape, including `catalog_name`,
`format_name`, `direction`, and `handler`. The validator reconciles each handler
with the same catalog's exported named functions. Repeated option rows do not
create surfaces or coverage. An absent or ambiguous handler, conflicting format
registrations, invalid direction, or format scoped to another catalog invalidates
that registration evidence. An unqualified handler shared by multiple schemas is
ambiguous; the validator does not guess which schema the worker invokes.

Keep the mapping's `reference` as the **qualified public handler**:

```json
{"cell": "rss-export", "reference": "feed.main.write_rss_copy"}
```

The mapped cell may then contain:

```sql
COPY (SELECT title, link FROM selected_items ORDER BY position)
TO 'artifacts/selected.rss'
(FORMAT 'feed.rss', title 'Selected items', link 'https://example.invalid/');
```

This counts only when the receipt-linked catalog's native export associates
`feed.rss`, catalog `feed`, and direction `to` (or `both`) with that exact public
handler. A registration in the current catalog cannot substitute for missing
registration evidence in the released runtime actually executed. The executed
alias must match both the handler reference and the format registration. Format
matching is case-insensitive, following the VGI binder.

Supported syntax is a top-level `COPY relation [(columns)] FROM/TO 'path' (...)`
or `COPY (query) TO 'path' (...)`, with one explicit scalar `FORMAT` option.
Multiple statements in a cell work. The parser distinguishes quoted identifiers
and string literals, skips comments and dollar-quoted contents, and matches the
direction and FORMAT option within the same COPY statement. Implicit formats,
dynamic format/path expressions, `COPY DATABASE`, `EXPLAIN`, prepared statements,
and FORMAT mentions inside SELECT labels, option values or comments do not earn
COPY coverage. Ordinary visible SELECT invocations retain their existing rules.

The same execution receipt, rendered results, narrative, and editorial review
requirements apply. A successful row count alone does not establish a meaningful
round trip or preservation claim; show and interpret the relevant read-back checks.

### Editorial review

Narrative references identify nonempty markdown. Results identify successfully
executed code cells with visible output. Interpretations identify markdown or
executed prose output. SQL and result cells may be the same cell. Editorial review
must still assess whether the question, invocation, result and interpretation form a
meaningful focused example; the validator cannot infer that from word count or parsing.

An approved example may explicitly apply to both released and current catalog hashes
after review of interface compatibility. Its **actual runtime revision is always
reported**, and `exact_runtime_count` separately counts examples executed at that
catalog's revision. A current-interface mapping approved against an older release is
not a claim that current-main code ran. New current-only names remain uncovered
release gaps until an appropriate runtime and reviewed example exist. For example,
6/6 released surfaces and 6/9 current surfaces must never be presented as 100% current
coverage; the current threshold for nine is nine. Changed signatures/kinds are also
reported under `interface_drift`.

Multiple notebooks and repeated references are unioned by logical surface, so they
never inflate the numerator. Unknown objects and stale/missing evidence are reported
on candidate mappings. Hash consistency cannot prove an honest executor or reviewer;
retain the real run logs and raw catalog evidence alongside these auditable attestations.
