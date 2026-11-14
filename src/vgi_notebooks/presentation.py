"""Consistent vector charts; analytical transformations belong in notebook SQL."""

from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import Markdown, display
from matplotlib_inline.backend_inline import set_matplotlib_formats


def theme():
    """Set typography, palette, whitespace and static SVG notebook output."""
    sns.set_theme(style="white", context="notebook", font_scale=1.05)
    plt.rcParams.update(
        {
            "figure.figsize": (10.8, 5.8),
            "figure.dpi": 150,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "text.color": "#243B2F",
            "axes.labelcolor": "#46574C",
            "xtick.color": "#46574C",
            "ytick.color": "#46574C",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.spines.left": False,
            "axes.spines.bottom": False,
            "axes.labelpad": 10,
            "grid.color": "#E5EBE7",
            "grid.linewidth": 0.7,
            "legend.frameon": False,
            "text.parse_math": False,
            "svg.fonttype": "path",
            "svg.hashsalt": "query-farm-vgi-examples",
        }
    )
    set_matplotlib_formats("svg")


def prose(text):
    display(Markdown(text))


def finish(fig, title, subtitle, source, *, name=None):
    """Publish a titled SVG figure with provenance and optional review artifacts."""
    fig.text(0.07, 0.97, title, fontsize=17, fontweight="bold", va="top")
    fig.text(0.07, 0.90, subtitle, fontsize=10.3, va="top", color="#52665A")
    fig.subplots_adjust(left=0.09, right=0.97, bottom=0.27, top=0.70 if fig.legends else 0.78, wspace=0.30)
    fig.text(0.07, 0.055, source, fontsize=8.2, va="bottom", color="#627468")
    if name:
        output = Path("artifacts/review")
        output.mkdir(parents=True, exist_ok=True)
        fig.savefig(output / f"{name}.svg", metadata={"Date": None}, bbox_inches="tight")
        fig.savefig(output / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.show()
