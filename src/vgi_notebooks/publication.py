"""Publish native SVG outputs as ordinary GitHub image assets as well."""

import hashlib
from html import escape
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote


_DATE_LINE = re.compile(r"^[ \t]*<dc:date\b[^>]*>.*?</dc:date>[ \t]*(?:\r?\n|$)", re.MULTILINE)
_DATE_ELEMENT = re.compile(r"<dc:date\b[^>]*>.*?</dc:date>", re.DOTALL)


def publish_svg_outputs(notebook, notebook_directory: Path) -> list[Path]:
    """Write hash-named SVGs and add GitHub image HTML without dropping native SVG."""
    descriptor = notebook.metadata["vgi_example"]
    relative_directory = PurePosixPath(descriptor["path"]).parent / "charts"
    directory = notebook_directory / "charts"
    generated = []
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            if "image/svg+xml" not in data:
                continue
            svg = data["image/svg+xml"]
            if isinstance(svg, list):
                svg = "".join(svg)
            svg = _DATE_ELEMENT.sub("", _DATE_LINE.sub("", svg))
            body = svg.encode("utf-8")
            filename = hashlib.sha256(body).hexdigest()[:16] + ".svg"
            path = directory / filename
            directory.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            repository = quote(descriptor["repository"], safe="/")
            relative_path = quote((relative_directory / filename).as_posix(), safe="/")
            url = f"https://raw.githubusercontent.com/{repository}/main/{relative_path}"
            data["image/svg+xml"] = svg
            data["text/html"] = (
                f'<img src="{escape(url, quote=True)}" '
                f'alt="{escape("Chart from notebook", quote=True)}" width="1100">'
            )
            if path not in generated:
                generated.append(path)
    return generated
