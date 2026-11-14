"""Launch registered Bun worker releases without a local source checkout.

Only setup diagnostics go to stderr; stdout is reserved for Arrow IPC. Released
TypeScript is interpreted directly, with its original frozen dependency lock.
"""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen
import zipfile

BUN_VERSION = "1.3.14"
# Official oven-sh/bun bun-v1.3.14/SHASUMS256.txt, checked 2026-11-14.
BUN_ASSETS = {
    ("Darwin", "arm64"): (
        "bun-darwin-aarch64",
        "d8b96221828ad6f97ac7ac0ab7e95872341af763001e8803e8267652c2652620",
    ),
    ("Darwin", "x86_64"): (
        "bun-darwin-x64-baseline",
        "3e35ad6f53971a9834bf9e6786e2adf72b5f1921cc9a9c5fde073d2972944076",
    ),
    ("Linux", "aarch64"): (
        "bun-linux-aarch64",
        "a27ffb63a8310375836e0d6f668ae17fa8d8d18b88c37c821c65331973a19a3b",
    ),
    ("Linux", "x86_64"): (
        "bun-linux-x64-baseline",
        "a063908ae08b7852ca10939bbdc6ceed3ddabce8fb9402dce83d65d73b36e6c7",
    ),
}
RELEASES = {
    "Query-farm/vgi-open-meteo@v0.4.0": {
        "commit": "67b18aedaf207cfea721121968bbec4ea0e0f735",
        "entrypoint": "src/bin/worker.ts",
    },
}


def cache_root():
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "vgi-notebooks"


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@contextmanager
def install_lock(destination, timeout=180):
    lock = destination.with_name(destination.name + ".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RuntimeError(f"Timed out waiting for installation lock: {lock}") from None
            time.sleep(0.25)
    try:
        yield
    finally:
        lock.rmdir()


def _run(args, cwd, capture=False):
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture else sys.stderr,
        stderr=sys.stderr,
        text=True,
        timeout=180,
    ).stdout


def _extract_verified(archive, expected, member, destination):
    if digest(archive) != expected:
        raise ValueError("Bun download SHA-256 does not match the official release")
    with zipfile.ZipFile(archive) as bundle:
        info = bundle.getinfo(member)
        if info.file_size > 250_000_000 or info.is_dir():
            raise ValueError("Unexpected Bun executable in release archive")
        # Extract just the expected member, never arbitrary archive paths.
        with bundle.open(info) as source, destination.open("xb") as target:
            shutil.copyfileobj(source, target)
    destination.chmod(0o755)


def ensure_bun():
    try:
        asset, expected = BUN_ASSETS[(platform.system(), platform.machine())]
    except KeyError:
        raise RuntimeError("This launcher supports macOS and glibc Linux on arm64 or x86_64") from None
    destination = cache_root() / "bun" / BUN_VERSION / asset
    with install_lock(destination):
        binary, marker = destination / "bun", destination / "sha256"
        if destination.exists():
            if not binary.is_file() or not marker.is_file() or digest(binary) != marker.read_text():
                raise ValueError(f"Bun cache verification failed; inspect {destination}")
            return binary
        with tempfile.TemporaryDirectory(prefix=".bun-", dir=destination.parent) as temporary:
            staging = Path(temporary)
            archive = staging / "download.zip"
            url = f"https://github.com/oven-sh/bun/releases/download/bun-v{BUN_VERSION}/{asset}.zip"
            with urlopen(url, timeout=60) as response, archive.open("xb") as output:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > 120_000_000:
                        raise ValueError("Bun download exceeds the expected size limit")
                    output.write(chunk)
            ready = staging / "ready"
            ready.mkdir()
            _extract_verified(archive, expected, asset + "/bun", ready / "bun")
            version = _run([str(ready / "bun"), "--version"], staging, capture=True).strip()
            if version != BUN_VERSION:
                raise ValueError("Bun executable version does not match the registered release")
            (ready / "sha256").write_text(digest(ready / "bun"))
            ready.rename(destination)
    return destination / "bun"


def _validate_checkout(checkout, spec):
    actual = _run(["git", "rev-parse", "HEAD"], checkout, capture=True).strip()
    dirty = _run(["git", "status", "--porcelain", "--untracked-files=no"], checkout, capture=True)
    entry = checkout / spec["entrypoint"]
    if actual != spec["commit"] or dirty or not entry.is_file():
        raise ValueError(f"Released worker cache/source verification failed: {checkout}")


def ensure_worker(release, bun):
    if release not in RELEASES:
        raise ValueError("Unknown worker release; choose one registered in this shared package")
    repository, tag = release.split("@")
    spec = RELEASES[release]
    destination = cache_root() / "workers" / repository / (spec["commit"] + "-bun-" + BUN_VERSION)
    with install_lock(destination):
        if destination.exists():
            if not (destination / ".vgi-notebook-ready").is_file():
                raise ValueError(f"Incomplete worker cache; inspect {destination}")
            _validate_checkout(destination, spec)
            return destination
        with tempfile.TemporaryDirectory(prefix=".worker-", dir=destination.parent) as temporary:
            staging = Path(temporary) / "source"
            staging.mkdir()
            _run(["git", "init", "--quiet"], staging)
            _run(["git", "remote", "add", "origin", f"https://github.com/{repository}.git"], staging)
            _run(["git", "fetch", "--quiet", "--depth", "1", "origin", "refs/tags/" + tag], staging)
            _run(["git", "checkout", "--quiet", "--detach", "FETCH_HEAD"], staging)
            _validate_checkout(staging, spec)
            if not any((staging / f).is_file() for f in ("bun.lock", "bun.lockb")):
                raise ValueError("Released worker has no frozen Bun lockfile")
            # Runtime dependencies are historically listed as devDependencies.
            # Skip package install hooks; never run build, prepack or worker tests.
            _run([str(bun), "install", "--frozen-lockfile", "--ignore-scripts"], staging)
            _validate_checkout(staging, spec)
            (staging / ".vgi-notebook-ready").write_text(json.dumps({"release": release, **spec}))
            staging.rename(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release", choices=sorted(RELEASES))
    parser.add_argument("worker_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        bun = ensure_bun()
        checkout = ensure_worker(args.release, bun)
        command = [str(bun), "run", str(checkout / RELEASES[args.release]["entrypoint"]), *args.worker_args]
        os.chdir(checkout)
        os.execv(str(bun), command)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"vgi-bun-worker: {error}", file=sys.stderr)
        raise SystemExit(1) from None
