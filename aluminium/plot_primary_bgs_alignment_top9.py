from pathlib import Path

import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D


BASE_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = BASE_DIR / "outputs"
FIGURES_DIR = OUTPUTS_DIR / "figures"

OLD_INPUT = OUTPUTS_DIR / "aluminium_primary_country_projection_2019_2050.csv"
ALIGNED_INPUT = (
    OUTPUTS_DIR / "aluminium_primary_country_projection_bgs_aligned_2019_2050.csv"
)
OUTPUT_PNG = FIGURES_DIR / "aluminium_primary_bgs_alignment_top9_2024_3x3.png"
OUTPUT_PDF = FIGURES_DIR / "aluminium_primary_bgs_alignment_top9_2024_3x3.pdf"

RANK_YEAR = 2024
START_YEAR = 2019
END_YEAR = 2050
COUNTRY_COUNT = 9

OLD_COLOR = "0.55"
ALIGNED_COLOR = "#0072B2"
OMNIA_COLOR = "#D55E00"


def read_projection(path):
    output = pd.read_csv(path)
    output.columns = [int(col) if str(col).isdigit() else col for col in output.columns]
    return output


def make_figure(
    country_count=COUNTRY_COUNT,
    nrows=3,
    ncols=3,
    figsize=(7.2, 6.7),
    output_png=OUTPUT_PNG,
    output_pdf=OUTPUT_PDF,
    top=0.84,
    bottom=0.08,
    hspace=0.24,
    legend_y=0.925,
    title_y=0.99,
):
    old = read_projection(OLD_INPUT)
    aligned = read_projection(ALIGNED_INPUT)
    years = list(range(START_YEAR, END_YEAR + 1))

    selected = (
        aligned[aligned["BGSRecordPresent"]]
        .sort_values(RANK_YEAR, ascending=False)
        .head(country_count)[["Country", "ISO3", RANK_YEAR]]
        .reset_index(drop=True)
    )
    if len(selected) != country_count:
        raise ValueError(
            f"Requested {country_count} countries but only found {len(selected)}."
        )

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

    fig, axes = plt.subplots(
        nrows,
        ncols,
        figsize=figsize,
        sharex=True,
        constrained_layout=False,
    )
    fig.subplots_adjust(
        left=0.09,
        right=0.99,
        bottom=bottom,
        top=top,
        hspace=hspace,
        wspace=0.20,
    )
    axes = axes.ravel()

    for ax, row in zip(axes, selected.itertuples(index=False)):
        old_row = old[old["ISO3"].eq(row.ISO3)].iloc[0]
        aligned_row = aligned[aligned["ISO3"].eq(row.ISO3)].iloc[0]

        old_values = [old_row[year] / 1000 for year in years]
        bgs_years = list(range(2020, 2025))
        bgs_values = [aligned_row[year] / 1000 for year in bgs_years]
        projection_years = list(range(2024, END_YEAR + 1))
        projection_values = [
            aligned_row[year] / 1000 for year in projection_years
        ]

        ax.plot(
            years,
            old_values,
            color=OLD_COLOR,
            linewidth=1.1,
            linestyle="--",
            zorder=1,
        )
        ax.plot(
            projection_years,
            projection_values,
            color=ALIGNED_COLOR,
            linewidth=1.55,
            zorder=2,
        )
        ax.scatter(
            bgs_years,
            bgs_values,
            color=ALIGNED_COLOR,
            s=9,
            linewidths=0,
            zorder=3,
        )
        ax.scatter(
            [2019],
            [aligned_row[2019] / 1000],
            color=OMNIA_COLOR,
            s=12,
            linewidths=0,
            zorder=4,
        )
        ax.axvline(2024.5, color="0.75", linewidth=0.55, linestyle=":")

        ax.set_title(f"{row.Country} ({row.ISO3})", loc="left", pad=3)
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
            marker="o",
            color=ALIGNED_COLOR,
            markerfacecolor=ALIGNED_COLOR,
            markersize=3.5,
            linewidth=1.55,
            label="BGS history and 2024-rebased projection",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="none",
            markerfacecolor=OMNIA_COLOR,
            markeredgecolor=OMNIA_COLOR,
            markersize=4,
            label="OMNIA 2019",
        ),
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, legend_y),
        ncol=3,
        frameon=False,
        fontsize=7,
        handlelength=2.4,
    )
    fig.supxlabel("Year", fontsize=8)
    fig.supylabel("Primary aluminium ingot production (Mt)", fontsize=8)
    fig.suptitle(
        "Old and BGS-aligned primary aluminium projections: "
        f"{country_count} largest 2024 producers",
        x=0.01,
        y=title_y,
        ha="left",
        fontsize=10,
        fontweight="bold",
    )

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, bbox_inches="tight")
    fig.savefig(output_pdf, bbox_inches="tight")
    plt.close(fig)

    return selected


if __name__ == "__main__":
    countries = make_figure()
    print(f"Saved: {OUTPUT_PNG}")
    print(f"Saved: {OUTPUT_PDF}")
    print("Countries included:")
    for row in countries.itertuples(index=False):
        print(f"  {row.Country} ({row.ISO3})")
