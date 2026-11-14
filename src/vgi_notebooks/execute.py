"""Execute the notebooks in fresh kernels and save their outputs after success."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

import nbformat
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager
from nbclient import NotebookClient

from .validation import validate_presentation
from .publication import publish_svg_outputs


def main() -> None:
    """Run selected notebooks, or all numbered examples, with this interpreter."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebooks", nargs="*", type=Path)
    parser.add_argument(
        "--parameters",
        default="{}",
        help="JSON object overriding visible parameters in a copy.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Save executed copies here, leaving the originals unchanged.",
    )
    parser.add_argument("--timeout", type=int, default=180, help="Maximum seconds per cell.")
    args = parser.parse_args()
    overrides = json.loads(args.parameters)
    if not isinstance(overrides, dict):
        parser.error("--parameters must be a JSON object")
    if overrides and args.output_dir is None:
        parser.error(
            "Use --output-dir with overrides to preserve the saved notebook's parameters and outputs."
        )
    if args.output_dir:
        args.output_dir = args.output_dir.resolve()
        args.output_dir.mkdir(parents=True, exist_ok=True)
    directory = Path.cwd().resolve()
    paths = args.notebooks or sorted(directory.glob("[0-9][0-9]_*.ipynb"))
    if not paths:
        parser.error("No numbered notebooks found; run from a worker notebooks directory")
    if args.output_dir and any((args.output_dir / p.name).resolve() == p.resolve() for p in paths):
        parser.error("Choose a separate output directory; overrides must preserve the source notebook.")
    os.environ["PLOOMBER_STATS_ENABLED"] = "false"

    # A temporary spec avoids changing the user's registered Jupyter kernels.
    with TemporaryDirectory(prefix="vgi-examples-kernel-") as temporary:
        kernel_dir = Path(temporary) / "vgi-examples"
        kernel_dir.mkdir()
        (kernel_dir / "kernel.json").write_text(
            json.dumps(
                {
                    "argv": [
                        sys.executable,
                        "-m",
                        "ipykernel_launcher",
                        "-f",
                        "{connection_file}",
                    ],
                    "display_name": "Python (vgi-examples notebooks)",
                    "language": "python",
                }
            )
        )
        for path in paths:
            path = path.resolve()
            notebook = nbformat.read(path, as_version=4)
            nbformat.validate(notebook)
            validate_presentation(notebook)
            parameter_cell = next(c for c in notebook.cells if "parameters" in c.metadata.get("tags", []))
            names = {
                node.targets[0].id
                for node in ast.parse(parameter_cell.source).body
                if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
            }
            if unknown := overrides.keys() - names:
                raise ValueError(f"Unknown parameters for {path.name}: {sorted(unknown)}")
            for key, value in overrides.items():
                parameter_cell.source = re.sub(
                    rf"^{re.escape(key)}\s*=.*$",
                    lambda _, name=key, replacement=value: f"{name} = {replacement!r}",
                    parameter_cell.source,
                    flags=re.MULTILINE,
                )
            manager = KernelManager(
                kernel_name="vgi-examples",
                kernel_spec_manager=KernelSpecManager(kernel_dirs=[temporary]),
            )
            print(f"Running {path.name} ...", flush=True)
            start = monotonic()
            client = NotebookClient(
                notebook,
                km=manager,
                timeout=args.timeout,
                allow_errors=False,
                resources={"metadata": {"path": str(directory)}},
            )
            try:
                client.execute(cleanup_kc=True)
            except Exception:
                print(f"FAILED: {path.name}; saved notebook left unchanged.", flush=True)
                raise
            nbformat.validate(notebook)
            for cell in notebook.cells:
                for output in cell.get("outputs", []):
                    rendered = json.dumps(output)
                    if output.get("output_type") == "error" or re.search(
                        r"\b(?:\w+\.)*\w*Warning:|/Users/|/home/rusty/", rendered
                    ):
                        failed = directory / "validation" / "failed-output-review.ipynb"
                        failed.parent.mkdir(exist_ok=True)
                        nbformat.write(notebook, failed)
                        raise ValueError(
                            "Unexpected warning, error, or local path in saved output; inspect validation/failed-output-review.ipynb"
                        )
            if args.output_dir is None:
                publish_svg_outputs(notebook, directory)
            destination = args.output_dir / path.name if args.output_dir else path
            if args.output_dir:
                for companion in directory.iterdir():
                    if args.output_dir.is_relative_to(companion.resolve()):
                        # Skip both the destination and its containing source branch.
                        continue
                    if companion.name in {
                        ".venv",
                        "validation",
                        "artifacts",
                        "__pycache__",
                        ".ruff_cache",
                        ".git",
                    }:
                        continue
                    if companion.is_dir():
                        shutil.copytree(companion, args.output_dir / companion.name, dirs_exist_ok=True)
                    elif companion.is_file() and companion.suffix != ".ipynb":
                        shutil.copy2(companion, args.output_dir / companion.name)
            staged = destination.with_suffix(".ipynb.tmp")
            nbformat.write(notebook, staged)
            staged.replace(destination)
            code_cells = [c for c in notebook.cells if c.cell_type == "code"]
            plots = sum(
                bool({"image/png", "image/svg+xml"} & o.get("data", {}).keys())
                for c in code_cells
                for o in c.outputs
            )
            print(
                f"OK: {len(code_cells)} code cells, {plots} charts, {monotonic() - start:.1f}s",
                flush=True,
            )
            if args.output_dir:
                print(f"Saved {destination}", flush=True)


if __name__ == "__main__":
    main()
