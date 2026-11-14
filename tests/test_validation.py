"""Only the documented released PII model may supplement a worker launch."""

import nbformat
import pytest

from vgi_notebooks.branding import footer, header
from vgi_notebooks.validation import validate_presentation


PII = (
    "uvx --python 3.13 --from git+https://github.com/Query-farm/vgi-pii@v0.4.0 "
    "--with https://github.com/explosion/spacy-models/releases/download/"
    "en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl vgi-pii-worker"
)


def notebook(location):
    descriptor = {"repository": "Query-farm/vgi-pii", "path": "notebooks/01_example.ipynb"}
    return nbformat.v4.new_notebook(
        metadata={"vgi_example": descriptor},
        cells=[
            nbformat.v4.new_markdown_cell(header(descriptor["repository"], descriptor["path"])),
            nbformat.v4.new_code_cell(f"%%sql\nATTACH 'pii' (TYPE vgi, LOCATION '{location}');"),
            nbformat.v4.new_markdown_cell(footer()),
        ],
    )


def test_released_pii_with_required_english_model_is_accepted():
    validate_presentation(notebook(PII))


@pytest.mark.parametrize(
    "location",
    [
        PII + " --with spacy==3.8.18",
        PII + " --with=spacy==3.8.18",
        PII.replace("--with ", "--with vgi-python==0.51.0 --with "),
        PII.replace("github.com/explosion/", "example.org/explosion/"),
        PII.replace("en_core_web_sm-3.8.0", "en_core_web_sm-3.7.1"),
        PII.replace("@v0.4.0", "@" + "a" * 40),
        PII.replace("@v0.4.0", "@main"),
        PII.replace("@v0.4.0", "@v0.5.0"),
        PII.replace("vgi-pii@", "another-worker@"),
        PII.replace("vgi-pii-worker", "python"),
        "uvx --from example --with=dependency==1 example",
    ],
)
def test_model_exception_does_not_allow_dependency_overrides_or_other_releases(location):
    with pytest.raises(ValueError, match="Use a released worker"):
        validate_presentation(notebook(location))


def test_plain_release_without_extra_dependency_keeps_working():
    validate_presentation(
        notebook("uvx --python 3.13 --from git+https://github.com/Query-farm/vgi-explain@v0.4.0 vgi-explain")
    )
