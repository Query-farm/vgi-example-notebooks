"""Validate catalog, execution and editorial evidence for notebook surface coverage.

This module reads artifacts; it never executes SQL or grants editorial approval.
Execution receipts and completeness reviews are explicit attestations from their
producers. Hashes detect stale or mismatched evidence, not a dishonest producer.
"""

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re


def file_sha256(path):
    """Hash exact artifact bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _source(cell):
    value = cell.get("source", "")
    return "".join(value) if isinstance(value, list) else value


def cell_source_sha256(cell):
    """Hash the exact joined UTF-8 source, without whitespace normalization."""
    return hashlib.sha256(_source(cell).encode("utf-8")).hexdigest()


def cell_outputs_sha256(cell):
    """Hash outputs using a reproducible JSON encoding."""
    body = json.dumps(cell.get("outputs", []), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def notebook_candidate_evidence(path):
    """Collect saved-cell fingerprints; these alone are not execution verification."""
    notebook = json.loads(Path(path).read_bytes())
    return {
        "status": "candidate",
        "notebook_sha256": file_sha256(path),
        "cells": [
            {
                "id": cell.get("id"),
                "execution_count": cell.get("execution_count"),
                "source_sha256": cell_source_sha256(cell),
                "outputs_sha256": cell_outputs_sha256(cell),
            }
            for cell in notebook["cells"]
            if cell.get("cell_type") == "code"
        ],
    }


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _text(value, label):
    _require(isinstance(value, str) and bool(value.strip()), f"Missing {label}")
    return value


def _time(value, label):
    parsed = datetime.fromisoformat(_text(value, label).replace("Z", "+00:00"))
    _require(parsed.utcoffset() is not None, f"{label} needs a timezone")


def _artifact(reference, root):
    _require(isinstance(reference, dict), "Missing artifact reference")
    relative = Path(_text(reference.get("path"), "artifact path"))
    _require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe artifact path")
    path = (root / relative).resolve()
    _require(path.is_relative_to(root), "Artifact escapes the coverage root")
    expected = reference.get("sha256", "")
    _require(
        isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected), "Missing artifact SHA-256"
    )
    body = path.read_bytes()
    _require(hashlib.sha256(body).hexdigest() == expected, f"Artifact hash mismatch: {relative}")
    return body


def _key(value):
    _require(isinstance(value, dict), "Missing object identity")
    schema = value.get("schema")
    if isinstance(schema, str):
        schema = [schema]
    _require(isinstance(schema, list) and bool(schema), "Object needs a schema path")
    parts = tuple(_text(part, "schema component").casefold() for part in schema)
    return parts, _text(value.get("name"), "object name").casefold()


def _identity(key):
    return {"schema": list(key[0]), "name": key[1]}


def _review(value):
    _require(
        isinstance(value, dict) and value.get("status") == "approved", "Editorial review is not approved"
    )
    _text(value.get("reviewer"), "reviewer")
    _time(value.get("reviewed_at"), "reviewed_at")


def _catalog(reference, root):
    result = {"verified": False, "objects": {}, "issues": []}
    try:
        if isinstance(reference, dict) and reference.get("status") == "unknown":
            raise ValueError(_text(reference.get("reason"), "unknown catalog reason"))
        data = json.loads(_artifact(reference, root))
        _require(data.get("schema_version") == 1, "Unsupported catalog schema_version")
        result.update(
            sha256=reference["sha256"],
            repository=_text(data.get("repository"), "catalog repository"),
            revision=_text(data.get("revision"), "catalog revision"),
            default_schema=_key({"schema": data.get("default_schema"), "name": "_"})[0],
        )
        _time(data.get("captured_at"), "catalog captured_at")
        rows = data.get("objects")
        _require(isinstance(rows, list), "Catalog objects must be a list")
        for row in rows:
            key = _key(row)
            kind = row.get("kind")
            _require(kind in {"function", "table"}, "Catalog object kind must be function or table")
            _require(
                not any(k in row for k in ("exclude", "excluded", "public")),
                "Catalog rows cannot exclude surfaces",
            )
            access = row.get("access", "unknown")
            authentication = row.get("authentication", "unknown")
            _require(access in {"read", "write", "read_write", "unknown"}, "Invalid object access")
            _require(
                authentication in {"required", "optional", "none", "unknown"}, "Invalid object authentication"
            )
            signatures = row.get("signatures", [])
            _require(
                isinstance(signatures, list) and all(isinstance(s, str) for s in signatures),
                "Invalid signatures",
            )
            obj = result["objects"].setdefault(
                key,
                {
                    **_identity(key),
                    "kinds": set(),
                    "signatures": set(),
                    "access": set(),
                    "authentication": set(),
                },
            )
            for field, values in (
                ("kinds", [kind]),
                ("signatures", signatures),
                ("access", [access]),
                ("authentication", [authentication]),
            ):
                obj[field].update(values)
        _require(bool(result["objects"]), "Empty catalog is not a verified zero-object denominator")
        _require(
            data.get("scope") == "all_public_functions_and_tables" and data.get("complete") is True,
            "Catalog does not attest complete public function/table scope",
        )
        evidence = data.get("evidence")
        _require(isinstance(evidence, list) and bool(evidence), "Missing catalog collection evidence")
        exported, export_columns = set(), set()
        for item in evidence:
            body = _artifact(item, root)
            _text(item.get("description"), "catalog evidence description")
            try:
                raw = json.loads(body)
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(raw, dict) or not isinstance(raw.get("columns"), list):
                continue
            columns = raw["columns"]
            for kind, column in (
                ("function", "function_name"),
                ("table", "table_name"),
                ("table", "view_name"),
            ):
                if "database_name" not in columns or "schema_name" not in columns or column not in columns:
                    continue
                export_columns.add(column)
                _require(isinstance(raw.get("rows"), list), "Catalog export is missing rows")
                for values in raw["rows"]:
                    _require(
                        isinstance(values, list) and len(values) == len(columns),
                        "Malformed catalog export row",
                    )
                    row = dict(zip(columns, values))
                    exported.add((kind, _key({"schema": row["schema_name"], "name": row[column]})))
        if export_columns:
            _require(
                {"function_name", "table_name"} <= export_columns,
                "Catalog export needs both function and table evidence, even when empty",
            )
            declared = {(kind, key) for key, obj in result["objects"].items() for kind in obj["kinds"]}
            _require(exported == declared, "Catalog snapshot omits or invents exported public objects")
        result["collection_reconciled"] = bool(export_columns)
        review = reference.get("review")
        _review(review)
        _require(review.get("catalog_sha256") == result["sha256"], "Catalog review is stale")
        _text(review.get("notes"), "catalog completeness review notes")
        result["verified"] = True
    except (ValueError, TypeError, KeyError, OSError, AttributeError) as exc:
        result["issues"].append(str(exc))
    return result


def _notebook(reference, root, catalogs):
    result = {"verified": False, "cells": {}, "issues": []}
    try:
        data = json.loads(_artifact(reference, root))
        result["sha256"] = reference["sha256"]
        for cell in data["cells"]:
            identifier = _text(cell.get("id"), "stable notebook cell ID")
            _require(identifier not in result["cells"], "Duplicate notebook cell ID")
            result["cells"][identifier] = cell
        receipt = json.loads(_artifact(reference.get("execution"), root))
        _require(
            receipt.get("schema_version") == 1 and receipt.get("status") == "success",
            "No successful execution receipt",
        )
        _require(receipt.get("notebook_sha256") == result["sha256"], "Execution receipt is stale")
        _time(receipt.get("executed_at"), "executed_at")
        _text(receipt.get("engine"), "execution engine")
        _text(receipt.get("command"), "execution command")
        matches = [
            c for c in catalogs.values() if c["verified"] and c["sha256"] == receipt.get("catalog_sha256")
        ]
        _require(bool(matches), "Execution receipt has no verified runtime catalog")
        runtime = matches[0]
        _require(
            receipt.get("worker_revision") == runtime["revision"],
            "Executed worker revision differs from runtime catalog",
        )
        aliases = receipt.get("catalog_aliases")
        _require(isinstance(aliases, list) and bool(aliases), "Missing executed catalog aliases")
        result["aliases"] = {_text(alias, "catalog alias").casefold() for alias in aliases}
        code_cells = {k: v for k, v in result["cells"].items() if v.get("cell_type") == "code"}
        _require(bool(code_cells), "Notebook has no code cells")
        recorded = {}
        for cell in receipt.get("cells", []):
            identifier = cell["id"]
            _require(identifier not in recorded, "Duplicate execution receipt cell")
            recorded[identifier] = cell
        _require(
            set(recorded) == set(code_cells), "Execution receipt must cover every code cell exactly once"
        )
        for identifier, cell in code_cells.items():
            _require(
                "skip-execution" not in cell.get("metadata", {}).get("tags", []),
                f"Skipped cell: {identifier}",
            )
            count = cell.get("execution_count")
            _require(type(count) is int and count > 0, f"Unexecuted cell: {identifier}")
            _require(
                not any(o.get("output_type") == "error" for o in cell.get("outputs", [])),
                f"Failed cell: {identifier}",
            )
            record = recorded[identifier]
            _require(
                record.get("status") == "success" and record.get("execution_count") == count,
                f"Cell lacks successful execution evidence: {identifier}",
            )
            _require(
                record.get("source_sha256") == cell_source_sha256(cell), f"Stale cell source: {identifier}"
            )
            _require(
                record.get("outputs_sha256") == cell_outputs_sha256(cell), f"Stale cell outputs: {identifier}"
            )
        result.update(verified=True, runtime=runtime, revision=runtime["revision"])
    except (ValueError, TypeError, KeyError, OSError, AttributeError) as exc:
        result["issues"].append(str(exc))
    return result


def _tokens(sql):
    """Lex identifiers/punctuation while discarding literals and nested comments."""
    tokens = []
    i = 0
    while i < len(sql):
        if sql.startswith("--", i):
            end = sql.find("\n", i)
            i = len(sql) if end < 0 else end + 1
        elif sql.startswith("/*", i):
            depth, i = 1, i + 2
            while i < len(sql) and depth:
                if sql.startswith("/*", i):
                    depth, i = depth + 1, i + 2
                elif sql.startswith("*/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
        elif sql[i] in "'\"":
            quote, value = sql[i], ""
            i += 1
            while i < len(sql):
                if quote == "'" and sql[i] == "\\" and i + 1 < len(sql):
                    # Conservatively treat escaped quotes as literal content, too.
                    value, i = value + sql[i : i + 2], i + 2
                    continue
                if sql[i] == quote:
                    if i + 1 < len(sql) and sql[i + 1] == quote:
                        value, i = value + quote, i + 2
                        continue
                    i += 1
                    break
                value, i = value + sql[i], i + 1
            tokens.append(value.casefold() if quote == '"' else None)
        elif match := re.match(r"\$(?:[A-Za-z_]\w*)?\$", sql[i:]):
            delimiter = match.group()
            end = sql.find(delimiter, i + len(delimiter))
            i = len(sql) if end < 0 else end + len(delimiter)
            tokens.append(None)
        elif match := re.match(r"[A-Za-z_][\w$]*", sql[i:]):
            tokens.append(match.group().casefold())
            i += len(match.group())
        else:
            if not sql[i].isspace():
                tokens.append(sql[i])
            i += 1
    return tokens


def _invokes(cell, reference, key, kinds, aliases, default_schema):
    source = _source(cell).strip()
    metadata = cell.get("metadata", {})
    if metadata.get("jupyter", {}).get("source_hidden") or set(metadata.get("tags", [])) & {
        "hide-input",
        "remove-input",
    }:
        return False
    if re.search(r"(?:^|\s)(?:-N|--no-execute)(?:\s|$)", source.partition("\n")[0]):
        return False
    if source.startswith("%%sql") and (len(source) == 5 or source[5].isspace()):
        source = source.partition("\n")[2]
    elif source.startswith("%sql "):
        source = source[5:]
    else:
        return False
    parts = _tokens(reference)
    if len(parts) < 3 or len(parts) % 2 == 0 or any(parts[i] != "." for i in range(1, len(parts), 2)):
        return False
    names = parts[::2]
    if not all(isinstance(n, str) and bool(n) for n in names) or names[0] not in aliases:
        return False
    suffix = tuple(names[1:])
    if suffix != (*key[0], key[1]) and not (key[0] == default_schema and suffix == (key[1],)):
        return False
    tokens = _tokens(source)
    for start in range(len(tokens) - len(parts) + 1):
        end = start + len(parts)
        if tokens[start:end] != parts or (start and tokens[start - 1] == "."):
            continue
        after = tokens[end] if end < len(tokens) else None
        before = tokens[start - 1] if start else None
        if after == "(" and "function" in kinds:
            return True
        if (
            after not in {"(", "."}
            and "table" in kinds
            and before in {"from", "join", "update", "into", "table", "copy"}
        ):
            return True
    return False


def _has_output(cell, text_only=False):
    metadata = cell.get("metadata", {})
    if metadata.get("jupyter", {}).get("outputs_hidden") or set(metadata.get("tags", [])) & {
        "hide-output",
        "remove-output",
    }:
        return False
    for output in cell.get("outputs", []):
        text = output.get("text", "")
        text = "".join(text) if isinstance(text, list) else text
        if output.get("output_type") == "stream" and text.strip():
            return True
        data = output.get("data", {})
        if any(
            value
            for mime, value in data.items()
            if not text_only or mime in {"text/markdown", "text/html", "text/plain"}
        ):
            return True
    return False


def _example(example, notebooks, catalogs):
    result = {"status": "candidate", "issues": [], "verified_catalogs": []}
    try:
        key = _key(example.get("object"))
        result.update(object=_identity(key), key=key, notebook=example.get("notebook"))
        book = notebooks.get(example.get("notebook"))
        _require(book is not None, "Unknown notebook reference")
        objects = [c["objects"][key] for c in catalogs.values() if key in c["objects"]]
        _require(bool(objects), "Unknown public object; no catalog row")
        runtime = book.get("runtime")
        kinds = runtime["objects"].get(key, {}).get("kinds", set()) if runtime else set()
        sql = example.get("sql")
        _require(isinstance(sql, list) and bool(sql), "Missing explicit SQL cell mappings")
        # Unexecuted/static references can be candidates, never verified.
        aliases = book.get("aliases", set())
        for invocation in sql:
            cell = book["cells"].get(invocation.get("cell"))
            _require(cell is not None and cell.get("cell_type") == "code", "Unknown SQL code cell")
            reference = _text(invocation.get("reference"), "SQL reference")
            if not book["verified"]:
                raise ValueError("No verified notebook execution: " + "; ".join(book["issues"]))
            _require(
                _invokes(cell, reference, key, kinds, aliases, runtime["default_schema"]),
                "Mapped cell does not visibly invoke the qualified public object",
            )
        _require(key in runtime["objects"], "Object is absent from the executed runtime catalog")
        for field in ("narrative_cells", "result_cells", "interpretation_cells"):
            references = example.get(field)
            _require(isinstance(references, list) and bool(references), f"Missing {field}")
            for identifier in references:
                cell = book["cells"].get(identifier)
                _require(cell is not None, f"Unknown {field} cell: {identifier}")
                if field == "narrative_cells":
                    _require(
                        cell.get("cell_type") == "markdown" and bool(_source(cell).strip()),
                        "Narrative must be nonempty markdown",
                    )
                elif field == "result_cells":
                    _require(
                        cell.get("cell_type") == "code" and _has_output(cell),
                        "Result must have successful rendered output",
                    )
                else:
                    _require(
                        (cell.get("cell_type") == "markdown" and bool(_source(cell).strip()))
                        or (cell.get("cell_type") == "code" and _has_output(cell, text_only=True)),
                        "Interpretation needs visible prose",
                    )
        review = example.get("review")
        _review(review)
        _require(review.get("notebook_sha256") == book["sha256"], "Example editorial review is stale")
        _text(review.get("purpose"), "editorial purpose")
        _text(review.get("finding"), "editorial finding")
        digests = review.get("catalog_sha256")
        _require(
            isinstance(digests, list) and bool(digests), "Editorial review must identify applicable catalogs"
        )
        known = {c.get("sha256") for c in catalogs.values() if c["verified"]}
        _require(all(d in known for d in digests), "Editorial review cites an unverified catalog")
        labels = [
            label
            for label, c in catalogs.items()
            if c["verified"] and c["sha256"] in digests and key in c["objects"]
        ]
        _require(bool(labels), "No reviewed catalog includes this object")
        result.update(
            status="verified",
            verified_catalogs=labels,
            runtime_revision=book["revision"],
            runtime_catalog_sha256=runtime["sha256"],
        )
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        result["issues"].append(str(exc))
    return result


def validate_coverage(manifest, root):
    """Return fail-closed released/current coverage metrics and evidence problems."""
    root = Path(root).resolve()
    issues = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        manifest = {}
        issues.append("Unsupported or missing coverage schema_version")
    descriptors = manifest.get("catalogs", {})
    if not isinstance(descriptors, dict):
        descriptors = {}
        issues.append("Catalog references must be an object")
    catalogs = {label: _catalog(reference, root) for label, reference in descriptors.items()}
    for label in ("released", "current"):
        catalogs.setdefault(label, _catalog(None, root))
    repositories = {c["repository"] for c in catalogs.values() if c["verified"]}
    if len(repositories) > 1:
        for catalog in catalogs.values():
            catalog["verified"] = False
            catalog["issues"].append("Catalogs refer to different worker repositories")
    notebooks = {}
    references = manifest.get("notebooks", [])
    mappings = manifest.get("examples", [])
    if not isinstance(references, list) or not isinstance(mappings, list):
        references, mappings = [], []
        issues.append("notebooks and examples must be lists")
    for reference in references:
        path = reference.get("path") if isinstance(reference, dict) else None
        if not isinstance(path, str) or not path.strip():
            issues.append("Notebook reference needs a nonempty path")
            continue
        if path in notebooks:
            notebooks[path]["verified"] = False
            notebooks[path]["issues"].append("Duplicate notebook reference")
        else:
            notebooks[path] = _notebook(reference, root, catalogs)
    examples = [_example(example, notebooks, catalogs) for example in mappings]
    metrics = {}
    for label, catalog in catalogs.items():
        covered = {e["key"] for e in examples if label in e["verified_catalogs"]}
        candidates = {e["key"] for e in examples if "key" in e and e["key"] in catalog["objects"]} - covered
        denominator = len(catalog["objects"]) if catalog["verified"] else None
        required = (
            (denominator if denominator <= 10 else (denominator + 1) // 2)
            if denominator is not None
            else None
        )
        runtime_exact = {
            e["key"]
            for e in examples
            if label in e["verified_catalogs"] and e["runtime_revision"] == catalog["revision"]
        }
        metrics[label] = {
            "catalog_status": "verified" if catalog["verified"] else "unknown",
            "revision": catalog.get("revision"),
            "catalog_sha256": catalog.get("sha256"),
            "collection_reconciled": catalog.get("collection_reconciled", False),
            "denominator": denominator,
            "observed_objects": len(catalog["objects"]),
            "required": required,
            "verified_count": len(covered),
            "candidate_count": len(candidates),
            "fraction": len(covered) / denominator if denominator else None,
            "meets_target": denominator is not None and len(covered) >= required,
            "exact_runtime_count": len(runtime_exact),
            "runtime_revisions": sorted(
                {e["runtime_revision"] for e in examples if label in e["verified_catalogs"]}
            ),
            "covered": [_identity(key) for key in sorted(covered)],
            "uncovered": [_identity(key) for key in sorted(set(catalog["objects"]) - covered)],
            "objects": [
                {k: sorted(v) if isinstance(v, set) else v for k, v in obj.items()}
                for _, obj in sorted(catalog["objects"].items())
            ],
            "issues": catalog["issues"],
        }
    released, current = catalogs["released"], catalogs["current"]
    drift = {"known": released["verified"] and current["verified"]}
    if drift["known"]:
        old, new = set(released["objects"]), set(current["objects"])
        drift.update(
            current_only=[_identity(k) for k in sorted(new - old)],
            released_only=[_identity(k) for k in sorted(old - new)],
            changed=[
                _identity(k) for k in sorted(old & new) if released["objects"][k] != current["objects"][k]
            ],
        )
    for example in examples:
        example.pop("key", None)
    return {
        "schema_version": 1,
        "status": "unknown"
        if not current["verified"]
        else ("met" if metrics["current"]["meets_target"] and not issues else "incomplete"),
        "meets_target": metrics["current"]["meets_target"] and not issues,
        "catalogs": metrics,
        "interface_drift": drift,
        "notebooks": {path: {k: b[k] for k in ("verified", "issues")} for path, b in notebooks.items()},
        "examples": examples,
        "issues": issues,
    }
