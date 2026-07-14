from pathlib import Path

import numpy as np
from matplotlib import pyplot as plt


ELASTICITY_POINTS = np.array(
    [
        (0.0, 1.264),
        (0.1, 1.1),
        (0.2, 1.109),
        (0.3, 0.6),
        (0.4, 0.336),
        (0.5, 0.18),
        (0.6, -0.027),
        (0.7, -0.041),
        (0.8, -0.252),
    ],
    dtype=float,
)

OUTPUT_PATH = Path(__file__).with_name("cement_income_elasticity.png")


def cement_income_elasticity(cement_intensity):
    """Linearly interpolate the elasticity curve used by the projection."""
    return np.interp(
        cement_intensity,
        ELASTICITY_POINTS[:, 0],
        ELASTICITY_POINTS[:, 1],
        left=ELASTICITY_POINTS[0, 1],
        right=ELASTICITY_POINTS[-1, 1],
    )


def make_figure():
    intensity = np.linspace(0.0, 0.8, 801)
    elasticity = cement_income_elasticity(intensity)

    fig, ax = plt.subplots(figsize=(7.2, 4.5), constrained_layout=True)
    ax.plot(intensity, elasticity, color="#0072B2", linewidth=2)
    ax.scatter(
        ELASTICITY_POINTS[:, 0],
        ELASTICITY_POINTS[:, 1],
        color="#D55E00",
        edgecolor="white",
        linewidth=0.7,
        s=42,
        zorder=3,
        label="Model points",
    )
    ax.axhline(0, color="0.25", linewidth=0.8, linestyle="--")

    ax.set(
        title="Cement income elasticity curve",
        xlabel="Cement intensity (tonnes per person)",
        ylabel="Income elasticity of cement intensity",
        xlim=(0, 0.8),
    )
    ax.grid(color="0.88", linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False)

    fig.savefig(OUTPUT_PATH, dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    make_figure()
    print(f"Saved: {OUTPUT_PATH}")
