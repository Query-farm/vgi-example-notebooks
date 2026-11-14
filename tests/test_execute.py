"""Real-kernel regressions for runner preservation, copying and output review."""

import sys

import nbformat
import pytest
from nbclient.exceptions import CellExecutionError

from vgi_notebooks import execute
from vgi_notebooks.branding import footer, header


def example(tmp_path, monkeypatch, source="print(VALUE)"):
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell("VALUE = 2", metadata={"tags": ["parameters"]}),
            nbformat.v4.new_code_cell(source),
        ]
    )
    path = tmp_path / "01_example.ipynb"
    nbformat.write(notebook, path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PLOOMBER_STATS_ENABLED", "false")
    # These tests isolate runner behavior; canonical presentation is checked below.
    monkeypatch.setattr(execute, "validate_presentation", lambda _: None)
    return path


def run(monkeypatch, *arguments):
    monkeypatch.setattr(sys, "argv", ["vgi-notebooks", *arguments])
    execute.main()


@pytest.mark.parametrize("destination", ["experiment", "experiments/band-10"])
def test_nested_output_is_excluded_and_override_preserves_original(tmp_path, monkeypatch, destination):
    path = example(tmp_path, monkeypatch)
    before = path.read_bytes()
    fixtures = tmp_path / "fixtures"
    fixtures.mkdir()
    (fixtures / "input.txt").write_text("example companion")
    (tmp_path / "helper.py").write_text("VALUE = 42\n")
    run(monkeypatch, "--parameters", '{"VALUE":10}', "--output-dir", destination)
    output = tmp_path / destination
    result = nbformat.read(output / path.name, as_version=4)
    assert result.cells[0].source == "VALUE = 10"
    assert result.cells[1].outputs[0].text == "10\n"
    assert (output / "fixtures/input.txt").read_text() == "example companion"
    assert (output / "helper.py").read_text() == "VALUE = 42\n"
    assert not (output / destination.split("/")[0]).exists()
    assert path.read_bytes() == before
    assert not list(output.glob("*.ipynb.tmp"))


@pytest.mark.parametrize("category", ["Warning", "UserWarning", "FutureWarning", "DeprecationWarning"])
def test_warning_output_preserves_prior_notebook(tmp_path, monkeypatch, category):
    path = example(
        tmp_path,
        monkeypatch,
        f"import warnings\nwarnings.simplefilter('always')\nwarnings.warn('review me', {category})",
    )
    before = path.read_bytes()
    with pytest.raises(ValueError, match="Unexpected warning"):
        run(monkeypatch)
    assert path.read_bytes() == before
    assert (tmp_path / "validation/failed-output-review.ipynb").is_file()
    assert not path.with_suffix(".ipynb.tmp").exists()


def test_failed_cell_preserves_prior_notebook(tmp_path, monkeypatch):
    path = example(tmp_path, monkeypatch, "raise ValueError('deliberate regression probe')")
    before = path.read_bytes()
    with pytest.raises(CellExecutionError, match="deliberate regression probe"):
        run(monkeypatch)
    assert path.read_bytes() == before
    assert not path.with_suffix(".ipynb.tmp").exists()


@pytest.mark.parametrize(
    ("arguments", "error"),
    [
        (["--parameters", '{"VALUE":10}'], SystemExit),
        (["--parameters", '{"UNKNOWN":10}', "--output-dir", "experiment"], ValueError),
        (["--parameters", '{"VALUE":10}', "--output-dir", "."], SystemExit),
    ],
)
def test_override_guards_preserve_original(tmp_path, monkeypatch, arguments, error):
    path = example(tmp_path, monkeypatch)
    before = path.read_bytes()
    with pytest.raises(error):
        run(monkeypatch, *arguments)
    assert path.read_bytes() == before


def test_header_drift_rejected_before_execution(tmp_path, monkeypatch):
    descriptor = {"repository": "Query-farm/example", "path": "notebooks/01_example.ipynb"}
    notebook = nbformat.v4.new_notebook(
        metadata={"vgi_example": descriptor},
        cells=[
            nbformat.v4.new_markdown_cell(header(descriptor["repository"], descriptor["path"])),
            nbformat.v4.new_code_cell("VALUE = 2", metadata={"tags": ["parameters"]}),
            nbformat.v4.new_code_cell("%%sql\nATTACH 'example' (TYPE vgi, LOCATION 'released-worker');"),
            nbformat.v4.new_markdown_cell(footer(descriptor["repository"])),
        ],
    )
    execute.validate_presentation(notebook)
    notebook.cells[0].source = notebook.cells[0].source.replace('width="252"', 'width="251"')
    path = tmp_path / "01_example.ipynb"
    nbformat.write(notebook, path)
    before = path.read_bytes()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="Header differs"):
        run(monkeypatch)
    assert path.read_bytes() == before
