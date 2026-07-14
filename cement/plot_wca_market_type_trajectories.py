"""Plot WCA regional market trajectories from the shared input CSV."""

from __future__ import annotations

from pathlib import Path

from matplotlib import pyplot as plt

from wca_regional_consumption import (
    WCA_MARKET_TYPES,
    WCA_YEARS,
    read_wca_regional_consumption,
)


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "inputs" / "wca_regional_cement_consumption.csv"
FIGURE_DIR = BASE_DIR / "outputs" / "figures"
FIGURE_STEM = FIGURE_DIR / "wca_market_type_trajectories_2x2"

YEARS = WCA_YEARS
MARKET_ORDER = WCA_MARKET_TYPES


def plot_trajectories(records: list[dict[str, str | float]]) -> None:
    plt.rcParams.update(
        {
            "font.size": 9,
            "axes.titlesize": 11,
            "axes.labelsize": 9,
            "legend.fontsize": 8,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.dpi": 150,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
        }
    )

    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True, constrained_layout=True)
    colors = plt.get_cmap("tab10").colors

    for ax, market_type in zip(axes.flat, MARKET_ORDER):
        market_records = [row for row in records if row["Market type"] == market_type]
        for color, row in zip(colors, market_records):
            values = [row[f"Consumption {year} (Mtpa)"] for year in YEARS]
            ax.plot(
                YEARS,
                values,
                color=color,
                linewidth=1.8,
                marker="o",
                markersize=4,
                label=str(row["Region"]),
            )

        ax.set_title(market_type, loc="left", fontweight="bold")
        ax.set_xticks(YEARS)
        ax.grid(axis="y", color="0.88", linewidth=0.7)
        ax.margins(x=0.04, y=0.1)
        ax.legend(frameon=False, loc="best")

    fig.supxlabel("Year")
    fig.supylabel("Cement consumption (Mtpa)")
    fig.suptitle("Regional cement consumption trajectories by market type", fontweight="bold")

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE_STEM.with_suffix(".png"), bbox_inches="tight")
    fig.savefig(FIGURE_STEM.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    records = read_wca_regional_consumption(INPUT_PATH)
    plot_trajectories(records)
    print(f"Input: {INPUT_PATH}")
    print(f"Saved: {FIGURE_STEM.with_suffix('.png')}")
    print(f"Saved: {FIGURE_STEM.with_suffix('.pdf')}")


if __name__ == "__main__":
    main()
