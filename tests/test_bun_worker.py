"""Release launcher boundaries: reject altered artifacts before execution."""

import hashlib
import io
from pathlib import Path
import subprocess
import zipfile

import pytest
from vgi_notebooks import bun_worker as worker


def archive(tmp_path):
    path = tmp_path / "bun.zip"
    with zipfile.ZipFile(path, "w") as bundle:
        bundle.writestr("official/bun", b"binary")
        bundle.writestr("../escaped", b"must not extract")
    return path


def test_archive_hash_checked_before_extraction(tmp_path):
    path = archive(tmp_path)
    with pytest.raises(ValueError, match="SHA-256"):
        worker._extract_verified(path, "wrong", "official/bun", tmp_path / "bun")
    assert not (tmp_path / "bun").exists()
    assert not (tmp_path.parent / "escaped").exists()


def test_only_expected_binary_is_extracted(tmp_path):
    path = archive(tmp_path)
    destination = tmp_path / "bun"
    worker._extract_verified(path, worker.digest(path), "official/bun", destination)
    assert destination.read_bytes() == b"binary"
    assert destination.stat().st_mode & 0o111
    assert not (tmp_path.parent / "escaped").exists()


def test_unsupported_platform_does_not_download(monkeypatch):
    monkeypatch.setattr(worker.platform, "system", lambda: "Windows")
    monkeypatch.setattr(worker, "urlopen", lambda *a, **kw: pytest.fail("no download"))
    with pytest.raises(RuntimeError, match="supports macOS"):
        worker.ensure_bun()


def test_corrupted_bun_cache_is_preserved_and_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "cache_root", lambda: tmp_path)
    monkeypatch.setattr(worker.platform, "system", lambda: "Linux")
    monkeypatch.setattr(worker.platform, "machine", lambda: "x86_64")
    path = tmp_path / "bun" / worker.BUN_VERSION / "bun-linux-x64-baseline"
    path.mkdir(parents=True)
    (path / "bun").write_bytes(b"changed")
    (path / "sha256").write_text(hashlib.sha256(b"original").hexdigest())
    monkeypatch.setattr(worker, "urlopen", lambda *a, **kw: pytest.fail("no download"))
    with pytest.raises(ValueError, match="cache verification"):
        worker.ensure_bun()
    assert (path / "bun").read_bytes() == b"changed"
    assert not path.with_name(path.name + ".lock").exists()


@pytest.mark.parametrize(
    "release", ["../arbitrary@v1", "Query-farm/vgi-open-meteo@main", "Query-farm/vgi-open-meteo@" + "a" * 40]
)
def test_only_registered_release_tags_are_accepted(release, monkeypatch):
    monkeypatch.setattr(worker, "cache_root", lambda: pytest.fail("no cache changes"))
    with pytest.raises(ValueError, match="Unknown worker release"):
        worker.ensure_worker(release, Path("/unused"))


def test_lock_timeout_preserves_other_owner(tmp_path):
    destination = tmp_path / "worker"
    lock = tmp_path / "worker.lock"
    lock.mkdir()
    with pytest.raises(RuntimeError, match="Timed out"):
        with worker.install_lock(destination, timeout=0):
            pytest.fail("must not enter")
    assert lock.is_dir()


@pytest.mark.parametrize("failure", ["moved-tag", "changed-source", "install"])
def test_failed_checkout_never_becomes_ready(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(worker, "cache_root", lambda: tmp_path)
    release = "Query-farm/vgi-open-meteo@v0.4.0"
    spec = worker.RELEASES[release]
    installed = []

    def run(args, cwd, capture=False):
        if args[0] == "/bun":
            installed.append(True)
            raise subprocess.CalledProcessError(1, args)
        if args[1:2] == ["checkout"]:
            entry = cwd / spec["entrypoint"]
            entry.parent.mkdir(parents=True)
            entry.write_text("released entry")
            (cwd / "bun.lock").write_text("lock")
        if args[1:2] == ["rev-parse"]:
            return "wrong" if failure == "moved-tag" else spec["commit"]
        if args[1:2] == ["status"]:
            return " M src/bin/worker.ts" if failure == "changed-source" else ""
        return ""

    monkeypatch.setattr(worker, "_run", run)
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        worker.ensure_worker(release, Path("/bun"))
    assert bool(installed) == (failure == "install")
    assert not list(tmp_path.rglob(".vgi-notebook-ready"))
    assert not list(tmp_path.rglob("*.lock"))
    assert not list(tmp_path.rglob(".worker-*"))


def test_bad_download_leaves_no_ready_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "cache_root", lambda: tmp_path)
    monkeypatch.setattr(worker.platform, "system", lambda: "Linux")
    monkeypatch.setattr(worker.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(worker, "urlopen", lambda *a, **kw: io.BytesIO(b"corrupt"))
    with pytest.raises(ValueError, match="SHA-256"):
        worker.ensure_bun()
    assert not list(tmp_path.rglob("sha256"))
    assert not list(tmp_path.rglob("*.lock"))
