"""Retrieve verified notebook companions for hosted runtimes such as Colab."""

from importlib.resources import files
from pathlib import Path
from urllib.request import urlopen
import hashlib
import json
import os
import sys


def _verified_file(path: Path, expected: str) -> bool:
    """Accept an existing companion only when its bytes match the pinned registry."""
    if not path.exists():
        return False
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Companion verification failed: {path} (SHA-256 mismatch; existing file unchanged)")
    return True


def prepare(example: str) -> Path:
    """Use local companions, or fetch the registry's pinned public example files."""
    if not example.replace("-", "").isalnum():
        raise ValueError("Invalid example identifier")
    manifest = json.loads(files("vgi_notebooks").joinpath("registry", example + ".json").read_text())
    for relative in manifest["files"]:
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Unsafe companion path")
    local_files = [
        _verified_file(Path.cwd() / path, expected) for path, expected in manifest["files"].items()
    ]
    if all(local_files):
        directory = Path.cwd()
    else:
        directory = Path.cwd() / ".vgi-examples" / example / manifest["revision"]
        directory.mkdir(parents=True, exist_ok=True)
        base = f"https://raw.githubusercontent.com/{manifest['repository']}/{manifest['revision']}/notebooks/"
        for relative, expected in manifest["files"].items():
            path = Path(relative)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe companion path")
            destination = directory / path
            if _verified_file(destination, expected):
                continue
            with urlopen(base + path.as_posix(), timeout=45) as response:
                body = response.read(10_000_001)
            if len(body) > 10_000_000 or hashlib.sha256(body).hexdigest() != expected:
                raise ValueError(f"Companion verification failed: {relative}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".download")
            temporary.write_bytes(body)
            temporary.replace(destination)
        os.chdir(directory)
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
    return directory
