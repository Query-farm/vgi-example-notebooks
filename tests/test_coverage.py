"""Constructed evidence fixtures test verification rules, not worker execution."""

from copy import deepcopy
import json

import pytest

from vgi_notebooks.coverage import (
    cell_outputs_sha256,
    cell_source_sha256,
    file_sha256,
    notebook_candidate_evidence,
    validate_coverage,
)


TIME = "2026-11-14T17:00:00Z"


class Evidence:
    def __init__(self, root, count=1, current_count=None):
        self.root = root
        self.manifest = {"schema_version": 1, "catalogs": {}, "notebooks": [], "examples": []}
        self.catalog("released", count, "release-1")
        self.catalog("current", count if current_count is None else current_count, "main-2")

    def write(self, path, data):
        destination = self.root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(data, indent=2) + "\n")
        return {"path": path, "sha256": file_sha256(destination)}

    def catalog(self, label, count, revision, extra=None):
        objects = [
            {
                "schema": "main",
                "name": f"f{i}",
                "kind": "function",
                "signatures": ["(INTEGER)"],
                "access": "write" if i == count - 1 else "read",
                "authentication": "required" if i == count - 1 else "none",
            }
            for i in range(count)
        ] + (extra or [])
        evidence = []
        for kind, column in (("function", "function_name"), ("table", "table_name")):
            export = self.write(
                f"coverage/{label}-{kind}.json",
                {
                    "query": f"complete worker {kind} export",
                    "columns": ["database_name", "schema_name", column],
                    "rows": [
                        ["worker", row["schema"], row["name"]] for row in objects if row["kind"] == kind
                    ],
                },
            )
            export["description"] = f"Unfiltered worker {kind} rows, including authenticated/write surfaces"
            evidence.append(export)
        snapshot = {
            "schema_version": 1,
            "repository": "Query-farm/example",
            "revision": revision,
            "captured_at": TIME,
            "default_schema": "main",
            "complete": True,
            "scope": "all_public_functions_and_tables",
            "evidence": evidence,
            "objects": objects,
        }
        reference = self.write(f"coverage/catalog-{label}.json", snapshot)
        reference["review"] = {
            "status": "approved",
            "reviewer": "test-reviewer",
            "reviewed_at": TIME,
            "catalog_sha256": reference["sha256"],
            "notes": "Checked complete public registration",
        }
        self.manifest["catalogs"][label] = reference

    def add_book(self, names, path="01_example.ipynb", sources=None, runtime="released"):
        cells = [
            {
                "id": "question",
                "cell_type": "markdown",
                "source": "Which transformation preserves the measure?",
            }
        ]
        for i, name in enumerate(names, 1):
            cells.append(
                {
                    "id": f"call-{i}",
                    "cell_type": "code",
                    "metadata": {},
                    "source": sources[i - 1] if sources else f"%%sql\nSELECT worker.main.{name}(1);",
                    "execution_count": i,
                    "outputs": [
                        {
                            "output_type": "execute_result",
                            "execution_count": i,
                            "metadata": {},
                            "data": {"text/plain": "1"},
                        }
                    ],
                }
            )
        cells.append(
            {
                "id": "finding",
                "cell_type": "markdown",
                "source": "The returned measure agrees; this fixture does not establish behavior for every input.",
            }
        )
        book = {"nbformat": 4, "nbformat_minor": 5, "metadata": {}, "cells": cells}
        reference = self.write(path, book)
        self.manifest["notebooks"].append(reference)
        for i, name in enumerate(names, 1):
            self.manifest["examples"].append(
                {
                    "object": {"schema": "main", "name": name},
                    "notebook": path,
                    "sql": [{"cell": f"call-{i}", "reference": f"worker.main.{name}"}],
                    "narrative_cells": ["question"],
                    "result_cells": [f"call-{i}"],
                    "interpretation_cells": ["finding"],
                    "review": {
                        "status": "approved",
                        "reviewer": "test-editor",
                        "reviewed_at": TIME,
                        "notebook_sha256": reference["sha256"],
                        "catalog_sha256": [r["sha256"] for r in self.manifest["catalogs"].values()],
                        "purpose": "Compare the measured transformation with the retained input",
                        "finding": "Returned measure agrees within this explicit fixture's scope",
                    },
                }
            )
        self.save_book(path, book, runtime)
        return book

    def save_book(self, path, book, runtime="released"):
        reference = next(r for r in self.manifest["notebooks"] if r["path"] == path)
        reference.update(self.write(path, book))
        catalog = self.manifest["catalogs"][runtime]
        snapshot = json.loads((self.root / catalog["path"]).read_text())
        receipt = {
            "schema_version": 1,
            "notebook_sha256": reference["sha256"],
            "catalog_sha256": catalog["sha256"],
            "worker_revision": snapshot["revision"],
            "status": "success",
            "executed_at": TIME,
            "engine": "constructed test receipt",
            "command": "unit-test fixture; not a claimed worker run",
            "catalog_aliases": ["worker"],
            "cells": [
                {
                    "id": c["id"],
                    "status": "success",
                    "execution_count": c["execution_count"],
                    "source_sha256": cell_source_sha256(c),
                    "outputs_sha256": cell_outputs_sha256(c),
                }
                for c in book["cells"]
                if c["cell_type"] == "code"
            ],
        }
        reference["execution"] = self.write(f"coverage/{path}.run.json", receipt)
        for example in self.manifest["examples"]:
            if example["notebook"] == path:
                example["review"]["notebook_sha256"] = reference["sha256"]

    def mutate_catalog(self, label, change):
        reference = self.manifest["catalogs"][label]
        data = json.loads((self.root / reference["path"]).read_text())
        change(data)
        reference.update(self.write(reference["path"], data))
        reference["review"]["catalog_sha256"] = reference["sha256"]

    def mutate_receipt(self, change):
        reference = self.manifest["notebooks"][0]["execution"]
        data = json.loads((self.root / reference["path"]).read_text())
        change(data)
        reference.update(self.write(reference["path"], data))

    def result(self):
        return validate_coverage(self.manifest, self.root)


@pytest.mark.parametrize(
    ("count", "covered", "required", "passes"),
    [
        (1, 1, 1, True),
        (10, 9, 10, False),
        (10, 10, 10, True),
        (11, 5, 6, False),
        (11, 6, 6, True),
        (17, 9, 9, True),
    ],
)
def test_exact_thresholds_include_authenticated_write_surfaces(tmp_path, count, covered, required, passes):
    e = Evidence(tmp_path, count)
    e.add_book([f"f{i}" for i in range(covered)])
    result = e.result()
    current = result["catalogs"]["current"]
    assert current["denominator"] == count
    assert current["required"] == required
    assert current["verified_count"] == covered
    assert result["meets_target"] is passes
    assert current["collection_reconciled"]
    write_object = next(o for o in current["objects"] if o["name"] == f"f{count - 1}")
    assert write_object["access"] == ["write"]
    assert write_object["authentication"] == ["required"]


def test_aliases_and_overloads_are_one_named_surface(tmp_path):
    e = Evidence(tmp_path)
    extra = [
        {"schema": "main", "name": "f0", "kind": "function", "signatures": ["(VARCHAR)"]},
        {"schema": "main", "name": "f0", "kind": "table"},
    ]
    e.catalog("released", 1, "release-1", extra)
    e.catalog("current", 1, "main-2", extra)
    e.add_book(["f0"])
    result = e.result()["catalogs"]["current"]
    assert result["denominator"] == result["verified_count"] == 1
    assert result["objects"][0]["kinds"] == ["function", "table"]
    assert result["objects"][0]["signatures"] == ["(INTEGER)", "(VARCHAR)"]


def test_multiple_notebooks_and_duplicate_references_do_not_inflate(tmp_path):
    e = Evidence(tmp_path, 2)
    e.add_book(["f0"])
    e.add_book(["f0", "f1"], "02_second.ipynb")
    e.manifest["examples"].append(deepcopy(e.manifest["examples"][0]))
    e.manifest["examples"][0]["sql"] *= 2
    assert e.result()["catalogs"]["current"]["verified_count"] == 2


def test_release_full_coverage_does_not_hide_current_release_gaps(tmp_path):
    e = Evidence(tmp_path, 6, current_count=9)
    e.add_book([f"f{i}" for i in range(6)])
    result = e.result()
    assert result["catalogs"]["released"]["meets_target"]
    current = result["catalogs"]["current"]
    assert current["verified_count"] == 6 and current["denominator"] == 9
    assert current["exact_runtime_count"] == 0 and current["runtime_revisions"] == ["release-1"]
    assert not result["meets_target"]
    assert [o["name"] for o in result["interface_drift"]["current_only"]] == ["f6", "f7", "f8"]


def test_current_execution_and_explicit_review_scope(tmp_path):
    e = Evidence(tmp_path)
    e.add_book(["f0"], runtime="current")
    e.manifest["examples"][0]["review"]["catalog_sha256"] = [e.manifest["catalogs"]["current"]["sha256"]]
    result = e.result()
    assert result["catalogs"]["current"]["exact_runtime_count"] == 1
    assert result["catalogs"]["released"]["verified_count"] == 0


@pytest.mark.parametrize(
    "source",
    [
        "%%sql\nSELECT 'worker.main.f0(1)';",
        "%%sql\n-- worker.main.f0(1)\nSELECT 1;",
        "%%sql\n/* outer /* inner */ worker.main.f0(1) */ SELECT 1;",
        "%%sql\nSELECT $tag$ worker.main.f0(1) $tag$;",
        "%%sql\nSELECT E'escaped\\' worker.main.f0(1)';",
        "%%sql\nSELECT other.main.f0(1);",
        "%%sql\nSELECT worker.main.f0 FROM local_table;",
        "con.execute('SELECT worker.main.f0(1)')",
    ],
)
def test_noninvocations_remain_candidates_even_with_execution_and_review(tmp_path, source):
    e = Evidence(tmp_path)
    e.add_book(["f0"], sources=[source])
    result = e.result()
    assert not result["meets_target"]
    assert result["examples"][0]["status"] == "candidate"
    assert result["catalogs"]["current"]["verified_count"] == 0


def test_quoted_and_default_schema_references(tmp_path):
    e = Evidence(tmp_path)
    e.add_book(["f0"], sources=['%%sql result <<\nSELECT "worker"."main"."f0"(1);'])
    e.manifest["examples"][0]["sql"][0]["reference"] = '"worker"."main"."f0"'
    assert e.result()["meets_target"]
    book = json.loads((tmp_path / "01_example.ipynb").read_text())
    book["cells"][1]["source"] = "%sql SELECT worker.f0(1);"
    e.save_book("01_example.ipynb", book)
    e.manifest["examples"][0]["sql"][0]["reference"] = "worker.f0"
    assert e.result()["meets_target"]


@pytest.mark.parametrize(
    "failure",
    [
        "unexecuted",
        "error",
        "missing-receipt",
        "candidate-receipt",
        "wrong-revision",
        "stale-output",
        "missing-cell",
    ],
)
def test_failed_unexecuted_or_unproven_notebooks_never_verify(tmp_path, failure):
    e = Evidence(tmp_path)
    book = e.add_book(["f0"])
    if failure == "unexecuted":
        book["cells"][1]["execution_count"] = None
        e.save_book("01_example.ipynb", book)
    elif failure == "error":
        book["cells"][1]["outputs"] = [
            {"output_type": "error", "ename": "ValueError", "evalue": "failed", "traceback": []}
        ]
        e.save_book("01_example.ipynb", book)
    elif failure == "missing-receipt":
        e.manifest["notebooks"][0].pop("execution")
    else:

        def change(receipt):
            if failure == "candidate-receipt":
                receipt["status"] = "candidate"
            elif failure == "wrong-revision":
                receipt["worker_revision"] = "different runtime"
            elif failure == "stale-output":
                receipt["cells"][0]["outputs_sha256"] = "0" * 64
            else:
                receipt["cells"] = []

        e.mutate_receipt(change)
    result = e.result()
    assert not result["notebooks"]["01_example.ipynb"]["verified"]
    assert not result["meets_target"]


@pytest.mark.parametrize(
    "failure",
    [
        "pending",
        "missing-purpose",
        "missing-finding",
        "stale-review",
        "hidden-sql",
        "empty-result",
        "missing-narrative",
        "missing-interpretation",
        "unknown-object",
        "unknown-cell",
    ],
)
def test_semantic_mapping_requires_explicit_editorial_and_cell_evidence(tmp_path, failure):
    e = Evidence(tmp_path)
    book = e.add_book(["f0"])
    item = e.manifest["examples"][0]
    if failure == "pending":
        item["review"]["status"] = "pending"
    elif failure.startswith("missing-") and failure.split("-")[1] in {"purpose", "finding"}:
        item["review"].pop(failure.split("-")[1])
    elif failure == "stale-review":
        item["review"]["notebook_sha256"] = "0" * 64
    elif failure == "hidden-sql":
        book["cells"][1]["metadata"] = {"jupyter": {"source_hidden": True}}
        e.save_book("01_example.ipynb", book)
    elif failure == "empty-result":
        book["cells"][1]["outputs"] = []
        e.save_book("01_example.ipynb", book)
    elif failure in {"missing-narrative", "missing-interpretation"}:
        item[failure.split("-")[1] + "_cells"] = []
    elif failure == "unknown-object":
        item["object"]["name"] = "not_in_catalog"
    else:
        item["sql"][0]["cell"] = "missing-cell"
    result = e.result()
    assert result["examples"][0]["status"] == "candidate"
    assert not result["meets_target"]


@pytest.mark.parametrize(
    "failure",
    [
        "unknown",
        "empty",
        "partial",
        "missing-raw",
        "bad-hash",
        "unreviewed",
        "omitted-write",
        "no-table-export",
        "exclusion",
    ],
)
def test_unknown_or_incomplete_catalog_cannot_become_zero_or_complete(tmp_path, failure):
    e = Evidence(tmp_path, 2)
    if failure == "unknown":
        e.manifest["catalogs"]["current"] = {
            "status": "unknown",
            "reason": "Current registration unavailable",
        }
    elif failure == "bad-hash":
        e.manifest["catalogs"]["current"]["sha256"] = "0" * 64
    elif failure == "unreviewed":
        e.manifest["catalogs"]["current"]["review"]["status"] = "pending"
    else:

        def change(data):
            if failure == "empty":
                data["objects"] = []
            elif failure == "partial":
                data["complete"] = False
            elif failure == "missing-raw":
                data["evidence"] = []
            elif failure == "omitted-write":
                data["objects"].pop()
            elif failure == "no-table-export":
                data["evidence"] = data["evidence"][:1]
            else:
                data["objects"][0]["exclude"] = True

        e.mutate_catalog("current", change)
    result = e.result()
    assert result["status"] == "unknown"
    assert result["catalogs"]["current"]["denominator"] is None
    assert result["catalogs"]["current"]["fraction"] is None
    assert not result["meets_target"]


def test_candidates_are_not_execution_receipts_and_no_runner_dependency(tmp_path):
    e = Evidence(tmp_path)
    e.add_book(["f0"])
    candidate = notebook_candidate_evidence(tmp_path / "01_example.ipynb")
    assert candidate["status"] == "candidate"
    assert all("status" not in cell for cell in candidate["cells"])
    assert "engine" not in candidate and "worker_revision" not in candidate


@pytest.mark.parametrize(
    "source",
    ["%%sql --save query --no-execute\nSELECT worker.main.f0(1);", "%sql -N SELECT worker.main.f0(1);"],
)
def test_saved_but_unexecuted_sql_is_not_coverage(tmp_path, source):
    e = Evidence(tmp_path)
    e.add_book(["f0"], sources=[source])
    assert not e.result()["meets_target"]


def test_skipped_cell_cannot_reuse_old_successful_outputs(tmp_path):
    e = Evidence(tmp_path)
    book = e.add_book(["f0"])
    book["cells"][1]["metadata"]["tags"] = ["skip-execution"]
    e.save_book("01_example.ipynb", book)
    assert not e.result()["notebooks"]["01_example.ipynb"]["verified"]


@pytest.mark.parametrize(
    ("source", "passes"),
    [
        ("%%sql\nSELECT * FROM worker.main.rows;", True),
        ("%%sql\nSELECT worker.main.rows FROM local_data;", False),
    ],
)
def test_table_reference_needs_relation_context(tmp_path, source, passes):
    e = Evidence(tmp_path)
    extra = [{"schema": "main", "name": "rows", "kind": "table"}]
    e.catalog("released", 0, "release-1", extra)
    e.catalog("current", 0, "main-2", extra)
    e.add_book(["rows"], sources=[source])
    assert e.result()["meets_target"] is passes


def test_invalid_notebook_path_reports_evidence_error(tmp_path):
    e = Evidence(tmp_path)
    e.manifest["notebooks"] = [{"path": {"malformed": True}}]
    result = e.result()
    assert not result["meets_target"]
    assert "Notebook reference needs a nonempty path" in result["issues"]


@pytest.mark.parametrize(
    "manifest",
    [{}, {"schema_version": 1, "notebooks": None, "examples": None}, {"schema_version": 1, "catalogs": []}],
)
def test_malformed_top_level_evidence_fails_closed(tmp_path, manifest):
    result = validate_coverage(manifest, tmp_path)
    assert not result["meets_target"] and result["status"] == "unknown"
    assert result["catalogs"]["current"]["denominator"] is None


def _view_evidence(evidence, label, name, *, physical_tables=False):
    """Add a native duckdb_views export; do not disguise it as duckdb_tables."""

    def update(snapshot):
        if not physical_tables:
            tables = next(item for item in snapshot["evidence"] if item["path"].endswith("-table.json"))
            raw = json.loads((evidence.root / tables["path"]).read_text())
            raw["rows"] = []
            tables.update(evidence.write(tables["path"], raw))
        view = evidence.write(
            f"coverage/{label}-views.json",
            {
                "query": "SELECT * FROM duckdb_views() WHERE database_name='worker'",
                "columns": ["database_name", "schema_name", "view_name"],
                "rows": [["worker", "main", name]],
            },
        )
        view["description"] = "Complete public native view export"
        snapshot["evidence"].append(view)

    evidence.mutate_catalog(label, update)


def test_native_view_union_with_empty_physical_tables(tmp_path):
    evidence = Evidence(tmp_path)
    for label, revision in [("released", "release-1"), ("current", "main-2")]:
        evidence.catalog(
            label,
            1,
            revision,
            extra=[{"schema": "main", "name": "supported_models", "kind": "table", "signatures": ["VIEW"]}],
        )
        _view_evidence(evidence, label, "supported_models")
    evidence.add_book(
        ["f0", "supported_models"],
        sources=[
            "%%sql\nSELECT worker.main.f0(1);",
            "%%sql\nSELECT * FROM worker.main.supported_models;",
        ],
    )
    report = evidence.result()
    assert report["meets_target"]
    assert report["catalogs"]["current"]["denominator"] == 2
    assert report["catalogs"]["current"]["verified_count"] == 2
    assert report["catalogs"]["current"]["collection_reconciled"]


def test_view_table_and_function_alias_share_one_logical_surface(tmp_path):
    evidence = Evidence(tmp_path)
    for label, revision in [("released", "release-1"), ("current", "main-2")]:
        evidence.catalog(
            label,
            1,
            revision,
            extra=[{"schema": "main", "name": "f0", "kind": "table", "signatures": ["VIEW", "TABLE"]}],
        )
        _view_evidence(evidence, label, "f0", physical_tables=True)
    evidence.add_book(["f0"], sources=["%%sql\nSELECT * FROM worker.main.f0;"])
    report = evidence.result()
    assert report["meets_target"]
    assert report["catalogs"]["current"]["denominator"] == 1
    assert report["catalogs"]["current"]["verified_count"] == 1


def test_unrecorded_public_view_invalidates_catalog(tmp_path):
    evidence = Evidence(tmp_path)
    _view_evidence(evidence, "current", "omitted_view")
    report = evidence.result()
    assert report["catalogs"]["current"]["denominator"] is None
    assert not report["meets_target"]
    assert "omits or invents" in str(report)


def test_views_cannot_replace_required_physical_table_export(tmp_path):
    evidence = Evidence(tmp_path)
    _view_evidence(evidence, "current", "f0")
    evidence.mutate_catalog(
        "current",
        lambda snapshot: snapshot.update(
            evidence=[item for item in snapshot["evidence"] if not item["path"].endswith("-table.json")]
        ),
    )
    report = evidence.result()
    assert report["catalogs"]["current"]["denominator"] is None
    assert "both function and table evidence" in str(report)
