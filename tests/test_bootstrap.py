"""Boundary checks for downloading code/data into a hosted notebook runtime."""

import hashlib
import io
import json
from pathlib import Path
import pytest
import vgi_notebooks.bootstrap as bootstrap


def registry(tmp_path, monkeypatch, names):
    data = tmp_path / "package" / "registry"
    data.mkdir(parents=True)
    manifest = {"repository": "Query-farm/example", "revision": "abc123", "files": names}
    (data / "example.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(bootstrap, "files", lambda _: tmp_path / "package")
    monkeypatch.setattr(bootstrap.sys, "path", bootstrap.sys.path.copy())
    cwd = tmp_path / "notebook"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    return cwd


def test_rejects_corrupted_download_before_import(tmp_path, monkeypatch):
    cwd = registry(tmp_path, monkeypatch, {"helper.py": hashlib.sha256(b"expected").hexdigest()})
    monkeypatch.setattr(bootstrap, "urlopen", lambda *a, **kw: io.BytesIO(b"unexpected"))
    with pytest.raises(ValueError, match="verification failed"):
        bootstrap.prepare("example")
    assert not list(cwd.rglob("helper.py"))
    assert Path.cwd() == cwd


def test_rejects_parent_path_before_download(tmp_path, monkeypatch):
    registry(tmp_path, monkeypatch, {"../../escaped.py": "unused"})
    monkeypatch.setattr(bootstrap, "urlopen", lambda *a, **kw: pytest.fail("must not download"))
    with pytest.raises(ValueError, match="Unsafe companion path"):
        bootstrap.prepare("example")


def test_verified_download_then_cache_reuse(tmp_path, monkeypatch):
    body = b"ANSWER = 42\n"
    registry(tmp_path, monkeypatch, {"helper.py": hashlib.sha256(body).hexdigest()})
    calls = []

    def response(*args, **kwargs):
        calls.append(args[0])
        return io.BytesIO(body)

    monkeypatch.setattr(bootstrap, "urlopen", response)
    directory = bootstrap.prepare("example")
    assert (directory / "helper.py").read_bytes() == body
    assert bootstrap.prepare("example") == directory
    assert len(calls) == 1


def test_verified_local_companions_do_not_download(tmp_path, monkeypatch):
    body = b"ANSWER = 42\n"
    cwd = registry(tmp_path, monkeypatch, {"helper.py": hashlib.sha256(body).hexdigest()})
    (cwd / "helper.py").write_bytes(body)
    monkeypatch.setattr(bootstrap, "urlopen", lambda *a, **kw: pytest.fail("must not download"))
    assert bootstrap.prepare("example") == cwd


@pytest.mark.parametrize("partial", [False, True])
def test_rejects_local_hash_mismatch_without_import_or_overwrite(tmp_path, monkeypatch, partial):
    files = {"missing.json": "unused"} if partial else {}
    files["helper.py"] = hashlib.sha256(b"expected").hexdigest()
    cwd = registry(tmp_path, monkeypatch, files)
    (cwd / "helper.py").write_bytes(b"corrupted")
    monkeypatch.setattr(bootstrap, "urlopen", lambda *a, **kw: pytest.fail("must not download"))
    previous_path = bootstrap.sys.path.copy()
    with pytest.raises(ValueError, match="helper.py.*SHA-256 mismatch"):
        bootstrap.prepare("example")
    assert (cwd / "helper.py").read_bytes() == b"corrupted"
    assert Path.cwd() == cwd
    assert bootstrap.sys.path == previous_path


@pytest.mark.parametrize("return_to_origin", [False, True])
def test_rejects_corrupted_cache_from_both_working_directories(tmp_path, monkeypatch, return_to_origin):
    body = b"ANSWER = 42\n"
    cwd = registry(tmp_path, monkeypatch, {"helper.py": hashlib.sha256(body).hexdigest()})
    monkeypatch.setattr(bootstrap, "urlopen", lambda *a, **kw: io.BytesIO(body))
    directory = bootstrap.prepare("example")
    (directory / "helper.py").write_bytes(b"corrupted cache")
    if return_to_origin:
        monkeypatch.chdir(cwd)
    before = Path.cwd()
    monkeypatch.setattr(bootstrap, "urlopen", lambda *a, **kw: pytest.fail("must not silently repair"))
    with pytest.raises(ValueError, match="helper.py.*SHA-256 mismatch"):
        bootstrap.prepare("example")
    assert (directory / "helper.py").read_bytes() == b"corrupted cache"
    assert Path.cwd() == before


def test_every_shipped_registry_can_be_prepared_locally(tmp_path, monkeypatch):
    """Published registry keys must be accepted by the actual notebook entry point."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(bootstrap.sys, "path", bootstrap.sys.path.copy())
    monkeypatch.setattr(bootstrap, "_verified_file", lambda *args: True)
    monkeypatch.setattr(bootstrap, "urlopen", lambda *args, **kwargs: pytest.fail("no download"))
    manifests = list(bootstrap.files("vgi_notebooks").joinpath("registry").iterdir())
    assert manifests
    for manifest in manifests:
        if manifest.name.endswith(".json"):
            assert bootstrap.prepare(manifest.name.removesuffix(".json")) == tmp_path
