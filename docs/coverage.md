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
`table`. Repeated overload/alias rows are merged case-insensitively using DuckDB's
identifier semantics. `authentication` accepts `none`, `optional`, `required`, or
`unknown`; `access` accepts `read`, `write`, `read_write`, or `unknown`. The latter
two fields may be omitted when not advertised and are then recorded as unknown;
the object still counts. There are no exclusion switches.

Collector JSON exports shaped as `{query, columns, rows}` are reconciled against the
snapshot whenever their columns include `database_name`, `schema_name`, and either
`function_name` or `table_name`. Both exports are required, including empty tables.
An omitted or invented exported object invalidates the denominator. Argument exports
are supplementary evidence, not a replacement for full function/table exports.

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
