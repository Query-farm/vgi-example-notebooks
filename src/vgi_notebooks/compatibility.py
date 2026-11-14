"""Detect libraries replaced on disk while an interactive kernel was running."""

from importlib.metadata import PackageNotFoundError, requires, version
import sys

from packaging.requirements import Requirement


def _check_colab_dependencies():
    try:
        requirements = requires("google-colab") or []
    except PackageNotFoundError:
        return
    conflicts = []
    for text in requirements:
        requirement = Requirement(text)
        if requirement.name.lower().replace("_", "-") not in {"ipykernel", "pandas", "jupyter-client"}:
            continue
        if requirement.marker and not requirement.marker.evaluate():
            continue
        installed = version(requirement.name)
        if installed not in requirement.specifier:
            conflicts.append(f"Colab requires {requirement}; installed {installed}")
    if conflicts:
        raise RuntimeError(
            "This Colab runtime has incompatible packages from an earlier installation. "
            "Save your work, choose Runtime → Disconnect and delete runtime, reconnect, "
            "and run the current notebook. Restarting the session alone will not restore "
            "Colab's original packages. " + "; ".join(conflicts)
        )


def check_runtime():
    """Stop before analysis if pip replaced a library already loaded by the kernel."""
    _check_colab_dependencies()
    changed = []
    for module_name, distribution in (
        ("matplotlib", "matplotlib"),
        ("pandas", "pandas"),
        ("numpy", "numpy"),
        ("IPython", "ipython"),
        ("ipykernel", "ipykernel"),
        ("jupyter_client", "jupyter-client"),
        ("matplotlib_inline", "matplotlib-inline"),
    ):
        module = sys.modules.get(module_name)
        loaded = getattr(module, "__version__", None)
        if loaded is None:
            continue
        try:
            installed = version(distribution)
        except PackageNotFoundError:
            continue
        if loaded != installed:
            changed.append(f"{distribution}: loaded {loaded}, installed {installed}")
    # Matplotlib can report its new disk version lazily even with an older Text class.
    text = sys.modules.get("matplotlib.text")
    if text is not None:
        installed = version("matplotlib")
        release = tuple(int(part) for part in installed.split(".")[:2])
        if release >= (3, 11) and not hasattr(text.Text, "get_fontfeatures"):
            changed.append("Matplotlib's loaded Text class predates its installed SVG renderer")
    if changed:
        raise RuntimeError(
            "Packages changed while this session was running. In Colab choose Runtime → Restart "
            "session, then Run all. In Jupyter restart the kernel, then run all. "
            "Do not reinstall or reload individual modules. " + "; ".join(changed)
        )
