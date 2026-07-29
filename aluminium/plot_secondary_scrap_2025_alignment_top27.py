from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

RANK_YEAR = 2024
START_YEAR = 2019
END_YEAR = 2050
COUNTRY_COUNT = 27
NROWS = 9
NCOLS = 3

OLD_COLOR = "0.55"

TITLE_NAME_OVERRIDES = {
    "Bosnia and Herzegovina": "Bosnia & Herz.",
    "Iran (Islamic Republic of)": "Iran",
    "Republic of Korea": "South Korea",
    "Russian Federation": "Russia",
    "United Arab Emirates": "UAE",
    "United Kingdom of Great Britain and Northern Ireland": "United Kingdom",
    "United States of America": "United States",
}

PLOTS = [
    {
        "name": "secondary",
        "old_input": (
            OUTPUTS_DIR
            / "aluminium_secondary_country_projection_2019_2050.csv"
        ),
        "aligned_input": (
            OUTPUTS_DIR
            / "aluminium_secondary_country_projection_2025_aligned_2019_2050.csv"
        ),
        "png": (
            FIGURES_DIR
            / "aluminium_secondary_2025_alignment_top27_2024_9x3.png"
        ),
        "pdf": (
            FIGURES_DIR
            / "aluminium_secondary_2025_alignment_top27_2024_9x3.pdf"
        ),
        "color": "#D55E00",
        "ylabel": "Secondary aluminium ingot production (Mt)",
        "title": (
            "Old and trend-aligned secondary aluminium projections: "
            "27 largest 2024 producers"
        ),
    },
    {
        "name": "scrap",
        "old_input": OUTPUTS_DIR / "aluminium_scrap_country_projection_2019_2050.csv",
        "aligned_input": (
            OUTPUTS_DIR
            / "aluminium_scrap_country_projection_2025_aligned_2019_2050.csv"
        ),
        "png": (
            FIGURES_DIR / "aluminium_scrap_2025_alignment_top27_2024_9x3.png"
        ),
        "pdf": (
            FIGURES_DIR / "aluminium_scrap_2025_alignment_top27_2024_9x3.pdf"
        ),
        "color": "#009E73",
        "ylabel": "Aluminium scrap (Mt)",
        "title": (
            "Old and trend-aligned aluminium scrap projections: "
            "27 largest 2024 country values"
        ),
    },
]


def read_projection(path):
    output = pd.read_csv(path)
    output.columns = [int(column) if str(column).isdigit() else column for column in output.columns]
    return output


def set_plot_theme():
    sns.set_theme(
        context="paper",
        style="white",
        font="Arial",
        rc={
            "axes.linewidth": 0.6,
            "axes.edgecolor": "0.15",
            "axes.labelcolor": "0.1",
            "axes.titlesize": 8,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "figure.dpi": 300,
            "savefig.dpi": 600,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        },
    )


def make_figure(config):
    old = read_projection(config["old_input"])
    aligned = read_projection(config["aligned_input"])
    years = list(range(START_YEAR, END_YEAR + 1))
    aligned_years = list(range(2024, END_YEAR + 1))

    selected = (
        aligned[aligned[RANK_YEAR].gt(0)]
        .sort_values(RANK_YEAR, ascending=False)
        .head(COUNTRY_COUNT)[["Country", "ISO3", RANK_YEAR]]
        .reset_index(drop=True)
    )
    if len(selected) != COUNTRY_COUNT:
        raise ValueError(
            f"{config['name']}: requested {COUNTRY_COUNT} positive producers "
            f"but found {len(selected)}."
        )

    set_plot_theme()
    fig, axes = plt.subplots(
        NROWS,
        NCOLS,
        figsize=(7.2, 18.0),
        sharex=True,
        constrained_layout=False,
    )
    fig.subplots_adjust(
        left=0.09,
        right=0.99,
        bottom=0.03,
        top=0.945,
        hspace=0.30,
        wspace=0.20,
    )
    axes = axes.ravel()

    for ax, row in zip(axes, selected.itertuples(index=False)):
        old_row = old[old["ISO3"].eq(row.ISO3)].iloc[0]
        aligned_row = aligned[aligned["ISO3"].eq(row.ISO3)].iloc[0]

        ax.plot(
            years,
            [old_row[year] / 1000 for year in years],
            color=OLD_COLOR,
            linewidth=1.1,
            linestyle="--",
            zorder=1,
        )
        ax.plot(
            aligned_years,
            [aligned_row[year] / 1000 for year in aligned_years],
            color=config["color"],
            linewidth=1.55,
            zorder=2,
        )
        ax.axvline(2024.5, color="0.75", linewidth=0.55, linestyle=":")

        display_country = TITLE_NAME_OVERRIDES.get(row.Country, row.Country)
        ax.set_title(f"{display_country} ({row.ISO3})", loc="left", pad=3)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.grid(axis="y", color="0.88", linewidth=0.45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(length=2.5, width=0.55, color="0.2", pad=2)
        ax.set_xlim(START_YEAR, END_YEAR)
        ax.set_xticks([2019, 2024, 2035, 2050])
        ax.margins(x=0)

    legend_handles = [
        Line2D(
            [0],
            [0],
            color=OLD_COLOR,
            linewidth=1.1,
            linestyle="--",
            label="Old approach",
        ),
        Line2D(
            [0],
            [0],
            color=config["color"],
            linewidth=1.55,
            label="2019–2024 trend-aligned approach",
        ),
        Line2D(
            [0],
            [0],
            color="0.75",
            linewidth=0.55,
            linestyle=":",
            label="Historical/model boundary",
        ),
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.968),
        ncol=3,
        frameon=False,
        fontsize=7,
        handlelength=2.4,
    )
    fig.supxlabel("Year", fontsize=8)
    fig.supylabel(config["ylabel"], fontsize=8)
    fig.suptitle(
        config["title"],
        x=0.01,
        y=0.995,
        ha="left",
        fontsize=10,
        fontweight="bold",
    )

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(config["png"], bbox_inches="tight")
    fig.savefig(config["pdf"], bbox_inches="tight")
    plt.close(fig)
    return selected


def main():
    for config in PLOTS:
        selected = make_figure(config)
        print(f"Saved: {config['png']}")
        print(f"Saved: {config['pdf']}")
        print(
            f"Countries included ({config['name']}): "
            + ", ".join(selected["ISO3"].tolist())
        )


if __name__ == "__main__":
    main()
