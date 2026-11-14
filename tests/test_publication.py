"""GitHub SVG assets preserve native output and ignore only volatile date metadata."""

import hashlib
from html.parser import HTMLParser
from urllib.parse import quote

import nbformat

from vgi_notebooks.publication import publish_svg_outputs


SVG = """<svg xmlns="http://www.w3.org/2000/svg" xmlns:dc="http://purl.org/dc/elements/1.1/">
 <metadata>
  <dc:date>{date}</dc:date>
  <dc:format>image/svg+xml</dc:format>
 </metadata>
 <text>2026-11-14 · café</text>
 <circle cx="5" cy="5" r="3" fill="green"/>
</svg>
"""


def notebook(*outputs, path="notebooks/01_example.ipynb"):
    return nbformat.v4.new_notebook(
        metadata={"vgi_example": {"repository": "Query-farm/example", "path": path}},
        cells=[nbformat.v4.new_code_cell("# chart", outputs=list(outputs))],
    )


def svg_output(svg):
    return nbformat.v4.new_output("display_data", data={"image/svg+xml": svg, "text/plain": "Chart"})


class Image(HTMLParser):
    def handle_starttag(self, tag, attrs):
        assert tag == "img"
        self.attributes = dict(attrs)


def test_writes_normalized_svg_and_escaped_github_html_retaining_native_mime(tmp_path):
    parent = 'examples/Research "&" notes'
    book = notebook(svg_output(SVG.format(date="2026-11-14T12:00:00")), path=parent + "/01_example.ipynb")
    paths = publish_svg_outputs(book, tmp_path)
    assert len(paths) == 1
    data = book.cells[0].outputs[0].data
    normalized = SVG.format(date="unused").replace("  <dc:date>unused</dc:date>\n", "")
    assert data["image/svg+xml"] == normalized
    assert data["text/plain"] == "Chart"
    assert paths[0].read_bytes() == normalized.encode("utf-8")
    assert paths[0].parent == tmp_path / "charts"
    assert paths[0].name == hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16] + ".svg"
    image = Image()
    image.feed(data["text/html"])
    assert image.attributes == {
        "src": "https://raw.githubusercontent.com/Query-farm/example/main/"
        + quote(parent + "/charts/" + paths[0].name, safe="/"),
        "alt": "Chart from notebook",
        "width": "1100",
    }
    assert "data:" not in data["text/html"]
    nbformat.validate(book)


def test_date_changes_and_missing_date_have_the_same_asset_hash(tmp_path):
    first = notebook(svg_output(SVG.format(date="2026-11-14T12:00:00")))
    second = notebook(svg_output(SVG.format(date="2027-01-01T01:02:03")))
    without_date = notebook(
        svg_output(SVG.format(date="unused").replace("  <dc:date>unused</dc:date>\n", ""))
    )
    paths = [publish_svg_outputs(book, tmp_path) for book in [first, second, without_date]]
    assert paths[0] == paths[1] == paths[2]
    assert len(list((tmp_path / "charts").glob("*.svg"))) == 1
    assert "2026-11-14 · café" in paths[0][0].read_text()
    assert "<dc:format>image/svg+xml</dc:format>" in paths[0][0].read_text()


def test_handles_multiple_outputs_and_cells_without_changing_other_mime(tmp_path):
    svg = SVG.format(date="2026-11-14T12:00:00")
    red = svg.replace('fill="green"', 'fill="red"')
    book = notebook(
        nbformat.v4.new_output("stream", name="stdout", text="kept\n"),
        svg_output(svg),
        nbformat.v4.new_output("display_data", data={"image/png": "YWJj", "text/html": "existing PNG HTML"}),
    )
    book.cells.append(
        nbformat.v4.new_code_cell("# next chart", outputs=[svg_output(red), svg_output(svg.splitlines(True))])
    )
    paths = publish_svg_outputs(book, tmp_path)
    assert len(paths) == 2
    assert all(path.is_file() for path in paths)
    assert book.cells[0].outputs[0].text == "kept\n"
    assert book.cells[0].outputs[2].data == {"image/png": "YWJj", "text/html": "existing PNG HTML"}
    assert book.cells[0].outputs[1].data["text/html"] == book.cells[1].outputs[1].data["text/html"]
    assert book.cells[0].outputs[1].data["text/html"] != book.cells[1].outputs[0].data["text/html"]
    assert all("image/svg+xml" in output.data for output in book.cells[1].outputs)
    nbformat.validate(book)


def test_no_svg_does_not_create_chart_directory(tmp_path):
    book = notebook(nbformat.v4.new_output("stream", name="stdout", text="no chart\n"))
    assert publish_svg_outputs(book, tmp_path) == []
    assert not (tmp_path / "charts").exists()
